"""Crypto strategy backtests with exchange fees and Indian VDA tax (research only)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from algorithmic_trading.backtester import run_backtest
from algorithmic_trading.strategy_lab import build_signals, normalise_price_frame
from crypto.instruments import PERIODS_PER_YEAR, FeeModel, tax_on_gain


@dataclass(frozen=True)
class CryptoResult:
    strategy: str
    signals: pd.Series
    curve: pd.DataFrame
    metrics: dict[str, float]
    trade_returns: pd.Series
    after_tax: dict[str, float]


def metrics_365(returns: pd.Series) -> dict[str, float]:
    r = pd.to_numeric(returns, errors="coerce").fillna(0.0)
    if len(r) < 2:
        return dict.fromkeys(("total_return", "cagr", "volatility", "sharpe", "max_drawdown"), 0.0)
    eq = (1.0 + r).cumprod()
    days = max((r.index[-1] - r.index[0]).days, 1)
    sd = float(r.std(ddof=1))
    final = float(eq.iloc[-1])
    return {
        "total_return": final - 1.0,
        "cagr": final ** (365.25 / days) - 1.0 if final > 0 else -1.0,
        "volatility": sd * np.sqrt(PERIODS_PER_YEAR),
        "sharpe": float(r.mean() / sd * np.sqrt(PERIODS_PER_YEAR)) if sd > 1e-12 else 0.0,
        "max_drawdown": float((eq / eq.cummax() - 1.0).min()),
    }


def trade_returns(position: pd.Series, strategy_return: pd.Series) -> pd.Series:
    """Compounded return of each uninterrupted position segment."""
    active = position.ne(0)
    starts = active & (~active.shift(1, fill_value=False) | position.ne(position.shift(1)))
    ids = starts.cumsum()[active]
    if ids.empty:
        return pd.Series(dtype=float)
    return (1.0 + strategy_return[active]).groupby(ids).prod() - 1.0


def after_tax_summary(trades: pd.Series, capital: float = 100_000.0) -> dict[str, float]:
    """Apply India's VDA rule per trade: 30% + cess on each gain, no relief for any loss.

    Treats each trade as using the full running capital (compounding on after-tax equity).
    Ignores the 1% TDS (a prepayment credited against tax) and the gain-on-cost nuance of
    multiple lots; it is an illustration of how harsh loss treatment is, not tax advice.
    """
    pre = post = capital
    paid = 0.0
    for t in trades:
        gain_pre = pre * t
        pre += gain_pre
        gain_post = post * t
        tax = tax_on_gain(gain_post)
        post += gain_post - tax
        paid += tax
    return {
        "pre_tax_final": pre,
        "after_tax_final": post,
        "tax_paid": paid,
        "pre_tax_return": pre / capital - 1.0,
        "after_tax_return": post / capital - 1.0,
    }


def run_crypto_backtest(
    frame: pd.DataFrame,
    strategy: str,
    *,
    fees: FeeModel | None = None,
    allow_short: bool = False,
    params: dict[str, float] | None = None,
    capital: float = 100_000.0,
) -> CryptoResult:
    model = fees or FeeModel()
    data = normalise_price_frame(frame)
    signals = build_signals(data, strategy, allow_short=allow_short, params=params)
    curve, _ = run_backtest(
        data["Close"], signals, initial_capital=capital, cost_bps=model.per_side_bps()
    )
    trades = trade_returns(curve["position"], curve["strategy_return"])
    return CryptoResult(
        strategy,
        signals,
        curve,
        metrics_365(curve["strategy_return"]),
        trades,
        after_tax_summary(trades, capital),
    )


def compare_crypto_strategies(
    frame: pd.DataFrame, strategies: tuple[str, ...], **kwargs
) -> pd.DataFrame:
    rows = {}
    for name in strategies:
        try:
            r = run_crypto_backtest(frame, name, **kwargs)
        except ValueError:
            continue
        data = normalise_price_frame(frame)
        bh = float(data["Close"].iloc[-1] / data["Close"].iloc[0] - 1.0)
        rows[name] = {
            **r.metrics,
            "trades": len(r.trade_returns),
            "after_tax_return": r.after_tax["after_tax_return"],
            "buy_hold_return": bh,
        }
    if not rows:
        raise ValueError("No strategy could be tested on this data.")
    return pd.DataFrame(rows).T.sort_values("sharpe", ascending=False)
