"""FX strategy backtests with spread costs and carry (research only).

Signals come from the Strategy Lab library; execution uses the standard backtester (a signal
at bar t trades bar t+1). Shorting the base currency is natural in FX, so ``allow_short`` is
on by default. Returns are on notional (unlevered); leverage multiplies both gains and losses
and adds margin-call risk that this simple model does not simulate.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from algorithmic_trading.backtester import run_backtest
from algorithmic_trading.momentum_portfolio import performance_metrics
from algorithmic_trading.strategy_lab import build_signals, normalise_price_frame
from forex.instruments import pip_size


@dataclass(frozen=True)
class FxResult:
    pair: str
    strategy: str
    signals: pd.Series
    curve: pd.DataFrame
    returns: pd.Series
    carry_return: pd.Series
    metrics: dict[str, float]
    trades: int


def run_fx_backtest(
    frame: pd.DataFrame,
    pair: str,
    strategy: str,
    *,
    spread_pips: float = 1.0,
    base_rate: float = 0.0,
    quote_rate: float = 0.0,
    allow_short: bool = True,
    leverage: float = 1.0,
    params: dict[str, float] | None = None,
) -> FxResult:
    if spread_pips < 0 or not 1.0 <= leverage <= 50:
        raise ValueError("spread_pips must be non-negative and leverage between 1 and 50")
    data = normalise_price_frame(frame)
    signals = build_signals(data, strategy, allow_short=allow_short, params=params)
    curve, _ = run_backtest(data["Close"], signals, cost_bps=0.0)
    # half the spread per unit traded (a full spread per round trip), priced at the prior close
    # so that no later price influences an earlier bar
    prior = data["Close"].shift(1).reindex(curve.index).bfill()
    spread_cost = curve["turnover"] * spread_pips * pip_size(pair) / (2.0 * prior)
    curve = curve.assign(
        transaction_cost=spread_cost,
        strategy_return=curve["position"] * curve["market_return"] - spread_cost,
    )
    gap_days = pd.Series(curve.index, index=curve.index).diff().dt.days.fillna(1.0)
    carry = curve["position"] * (base_rate - quote_rate) * gap_days / 365.0
    net = (curve["strategy_return"] + carry) * leverage
    net = net.clip(lower=-1.0)  # a bar cannot lose more than the account
    curve = curve.assign(carry_return=carry, net_return=net, net_equity=(1.0 + net).cumprod())
    entries = int(
        (
            (curve["position"] != 0) & (curve["position"].shift(1).fillna(0.0) != curve["position"])
        ).sum()
    )
    return FxResult(pair, strategy, signals, curve, net, carry, performance_metrics(net), entries)


def compare_fx_strategies(
    frame: pd.DataFrame, pair: str, strategies: tuple[str, ...], **kwargs
) -> pd.DataFrame:
    rows = {}
    for name in strategies:
        try:
            r = run_fx_backtest(frame, pair, name, **kwargs)
        except ValueError:
            continue
        rows[name] = {**r.metrics, "trades": r.trades, "carry earned": float(r.carry_return.sum())}
    if not rows:
        raise ValueError("No strategy could be tested on this data.")
    return pd.DataFrame(rows).T.sort_values("sharpe", ascending=False)
