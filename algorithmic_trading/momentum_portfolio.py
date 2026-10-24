"""Cross-sectional momentum portfolio backtester (research only).

At each rebalance the portfolio ranks the universe by trailing momentum, holds the top
names (equal or inverse-volatility weighted) and goes to cash when nothing is trending up
or when an optional market gate is off. Rules that keep it honest:

* Targets are decided from data up to and including the rebalance bar's close and are held
  from the *next* bar, exactly like the single-asset backtester, so there is no look-ahead.
* Between rebalances weights drift with prices (no free daily rebalancing).
* Trading costs are charged on the actual buys and sells needed to move from the drifted
  weights to the new targets, using the flat bps or the NSE cost model.
* Fees are paid out of cash, so a fully invested book can carry a cash balance a fraction of
  a percent below zero. This is a small modelling simplification and is identical for the
  strategy and its benchmark.
* Metrics start at the first investable bar, so the warm-up period does not flatter them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from algorithmic_trading.advanced_strategies import momentum_scores
from algorithmic_trading.trading_costs import IndiaEquityCostModel

TRADING_DAYS = 252
WEIGHTINGS = ("equal", "inverse_volatility")

TargetFn = Callable[[pd.DataFrame], pd.Series]


@dataclass(frozen=True)
class PortfolioResult:
    returns: pd.Series  # net daily portfolio return
    equity: pd.Series  # growth of 1 starting at the first investable bar
    weights: pd.DataFrame  # weights held during each bar (after the previous bar's rebalance)
    turnover: pd.Series  # one-way traded fraction of equity per bar
    rebalances: pd.DataFrame  # one row per rebalance: date, holdings
    metrics: dict[str, float]


def clean_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Numeric, sorted, de-duplicated close prices; non-positive values become missing."""
    if prices is None or prices.empty:
        raise ValueError("No price data was provided.")
    frame = prices.apply(pd.to_numeric, errors="coerce")
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    frame = frame.where(frame > 0)
    frame = frame.dropna(axis=1, how="all")
    if frame.shape[1] == 0:
        raise ValueError("No usable price columns.")
    return frame


def performance_metrics(returns: pd.Series) -> dict[str, float]:
    """Total return, CAGR, volatility, Sharpe and max drawdown of daily returns."""
    values = pd.to_numeric(returns, errors="coerce").fillna(0.0)
    if len(values) < 2:
        return dict.fromkeys(("total_return", "cagr", "volatility", "sharpe", "max_drawdown"), 0.0)
    equity = (1.0 + values).cumprod()
    days = max((values.index[-1] - values.index[0]).days, 1)
    final = float(equity.iloc[-1])
    std = float(values.std(ddof=1))
    return {
        "total_return": final - 1.0,
        "cagr": final ** (365.25 / days) - 1.0 if final > 0 else -1.0,
        "volatility": std * np.sqrt(TRADING_DAYS),
        "sharpe": float(values.mean() / std * np.sqrt(TRADING_DAYS)) if std > 1e-12 else 0.0,
        "max_drawdown": float((equity / equity.cummax() - 1.0).min()),
    }


# --------------------------------------------------------------------------------------
# target-weight rules
# --------------------------------------------------------------------------------------
def momentum_target(
    top_n: int,
    lookback: int,
    skip: int,
    weighting: str = "equal",
    vol_window: int = 60,
    require_positive: bool = True,
) -> TargetFn:
    """Target-weight function: top momentum names, equal or inverse-volatility weighted."""
    if weighting not in WEIGHTINGS:
        raise ValueError(f"weighting must be one of {WEIGHTINGS}")
    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    def target(history: pd.DataFrame) -> pd.Series:
        scores = momentum_scores(history, lookback, skip).dropna()
        if require_positive:
            scores = scores[scores > 0]
        leaders = scores.sort_values(ascending=False, kind="stable").head(top_n).index
        weights = pd.Series(0.0, index=history.columns)
        if len(leaders) == 0:
            return weights
        if weighting == "equal":
            weights.loc[leaders] = 1.0 / len(leaders)
            return weights
        vol = history[leaders].pct_change().tail(vol_window).std(ddof=1)
        inverse = 1.0 / vol.where(vol > 1e-9)
        if inverse.isna().any() or not np.isfinite(inverse).all():
            weights.loc[leaders] = 1.0 / len(leaders)  # fall back if volatility is unusable
            return weights
        weights.loc[leaders] = inverse / inverse.sum()
        return weights

    return target


def equal_weight_target(history: pd.DataFrame) -> pd.Series:
    """Hold every symbol that has a price today, equally weighted (the naive benchmark)."""
    live = history.iloc[-1].notna()
    weights = pd.Series(0.0, index=history.columns)
    if live.any():
        weights.loc[live[live].index] = 1.0 / int(live.sum())
    return weights


# --------------------------------------------------------------------------------------
# simulation engine
# --------------------------------------------------------------------------------------
def simulate_portfolio(
    prices: pd.DataFrame,
    target_fn: TargetFn,
    *,
    first_rebalance: int,
    rebalance_every: int = 21,
    cost_bps: float = 10.0,
    cost_model: IndiaEquityCostModel | None = None,
    gate: pd.Series | None = None,
) -> PortfolioResult:
    """Run a rebalanced long-only portfolio; see the module docstring for the conventions."""
    data = clean_prices(prices)
    if rebalance_every < 1:
        raise ValueError("rebalance_every must be at least 1")
    if not np.isfinite(cost_bps) or cost_bps < 0:
        raise ValueError("cost_bps must be finite and non-negative")
    n, m = data.shape
    if first_rebalance < 1 or first_rebalance >= n - 1:
        raise ValueError("Not enough history for a single rebalance.")

    filled = data.ffill()
    asset_returns = filled.pct_change().fillna(0.0).to_numpy()
    index = data.index
    gate_values = None if gate is None else gate.reindex(index).fillna(False).to_numpy(dtype=bool)

    held = np.zeros(m)  # weights during the current bar
    cash = 1.0
    weights_log = np.zeros((n, m))
    port_returns = np.zeros(n)
    turnover = np.zeros(n)
    pending: np.ndarray | None = None  # target chosen at the previous bar's close
    rebalance_rows = []
    buy_rate_flat = cost_bps / 10_000.0

    for t in range(n):
        traded_buy = traded_sell = 0.0
        if pending is not None:
            diff = pending - held
            traded_buy = float(diff[diff > 0].sum())
            traded_sell = float(-diff[diff < 0].sum())
            held = pending
            cash = 1.0 - float(held.sum())
            pending = None
        weights_log[t] = held
        turnover[t] = traded_buy + traded_sell

        if cost_model is None:
            cost = (traded_buy + traded_sell) * buy_rate_flat
        else:
            cost = float(
                cost_model.cost_fraction(pd.Series([traded_buy]), pd.Series([traded_sell])).iloc[0]
            )
        gross = float(held @ asset_returns[t])
        equity_after = 1.0 + gross - cost
        port_returns[t] = gross - cost
        if equity_after > 0:
            held = held * (1.0 + asset_returns[t]) / equity_after
            cash = (cash - cost) / equity_after

        is_rebalance = t >= first_rebalance and (t - first_rebalance) % rebalance_every == 0
        if is_rebalance and t < n - 1:
            history = data.iloc[: t + 1]
            target = target_fn(history).reindex(data.columns).fillna(0.0)
            if gate_values is not None and not gate_values[t]:
                target = target * 0.0
            target_values = np.clip(target.to_numpy(dtype=float), 0.0, None)
            total = target_values.sum()
            if total > 1.0 + 1e-9:
                target_values = target_values / total  # never lever up
            pending = target_values
            rebalance_rows.append(
                {
                    "date": index[t],
                    "holdings": ", ".join(
                        f"{sym} {w:.0%}"
                        for sym, w in zip(data.columns, target_values, strict=True)
                        if w > 0
                    )
                    or "cash",
                    "names": int((target_values > 0).sum()),
                }
            )

    start = first_rebalance + 1
    returns = pd.Series(port_returns, index=index).iloc[start:]
    return PortfolioResult(
        returns=returns,
        equity=(1.0 + returns).cumprod(),
        weights=pd.DataFrame(weights_log, index=index, columns=data.columns).iloc[start:],
        turnover=pd.Series(turnover, index=index).iloc[start:],
        rebalances=pd.DataFrame(rebalance_rows),
        metrics=performance_metrics(returns),
    )


def run_momentum_portfolio(
    prices: pd.DataFrame,
    *,
    top_n: int = 5,
    lookback: int = 252,
    skip: int = 21,
    rebalance_every: int = 21,
    weighting: str = "equal",
    vol_window: int = 60,
    require_positive: bool = True,
    cost_bps: float = 10.0,
    cost_model: IndiaEquityCostModel | None = None,
    gate: pd.Series | None = None,
) -> tuple[PortfolioResult, PortfolioResult]:
    """Momentum portfolio and the equal-weight benchmark over the same dates and costs."""
    target = momentum_target(top_n, lookback, skip, weighting, vol_window, require_positive)
    kwargs = {
        "first_rebalance": lookback,
        "rebalance_every": rebalance_every,
        "cost_bps": cost_bps,
        "cost_model": cost_model,
    }
    strategy = simulate_portfolio(prices, target, gate=gate, **kwargs)  # type: ignore[arg-type]
    benchmark = simulate_portfolio(prices, equal_weight_target, **kwargs)  # type: ignore[arg-type]
    return strategy, benchmark
