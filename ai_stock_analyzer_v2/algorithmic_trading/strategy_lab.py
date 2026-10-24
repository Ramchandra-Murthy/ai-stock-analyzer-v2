"""Glue between the systematic strategy library and the backtester.

Pure functions (no Streamlit, no network) so the Strategy Lab page stays thin and every
code path here can be unit tested. Signals come from ``advanced_strategies``; execution,
costs and metrics come from ``backtester.run_backtest`` (signal at bar *t* trades bar
*t+1*, so there is no look-ahead).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from algorithmic_trading.advanced_strategies import (
    donchian_breakout_signals,
    ensemble_vote,
    rsi2_pullback_signals,
    supertrend_signals,
    volatility_target_scale,
    zscore_mean_reversion_signals,
)
from algorithmic_trading.backtester import BacktestMetrics, run_backtest
from algorithmic_trading.regime_filter import apply_regime_gate
from algorithmic_trading.trading_costs import IndiaEquityCostModel

STRATEGIES = (
    "Supertrend",
    "Donchian breakout",
    "Z-score mean reversion",
    "RSI(2) pullback",
    "Ensemble (all four)",
)
REQUIRED_COLUMNS = ("High", "Low", "Close")


@dataclass(frozen=True)
class StrategyLabResult:
    """Backtest output plus the signal that produced it."""

    strategy: str
    signals: pd.Series
    curve: pd.DataFrame
    metrics: BacktestMetrics


def normalise_price_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a clean OHLC frame with flat columns, a sorted unique index and valid prices.

    Accepts yfinance-style output, including the ``(field, ticker)`` MultiIndex columns it
    produces for single-ticker downloads, and raises ``ValueError`` if it is unusable.
    """
    if frame is None or frame.empty:
        raise ValueError("No price data was returned for this symbol.")
    data = frame.copy()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data = data.loc[:, ~data.columns.duplicated()]
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError(f"Price data is missing columns: {', '.join(missing)}")
    for column in REQUIRED_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=list(REQUIRED_COLUMNS))
    data = data[data["Close"] > 0]
    data = data[~data.index.duplicated(keep="last")].sort_index()
    if len(data) < 2:
        raise ValueError("Not enough valid price history to run a backtest.")
    return data


def build_signals(
    frame: pd.DataFrame,
    strategy: str,
    *,
    allow_short: bool = False,
    params: dict[str, float] | None = None,
) -> pd.Series:
    """Target positions in {-1, 0, 1} for the named strategy (see ``STRATEGIES``)."""
    params = params or {}
    close = frame["Close"]

    def supertrend() -> pd.Series:
        return supertrend_signals(
            frame,
            period=int(params.get("st_period", 10)),
            multiplier=float(params.get("st_multiplier", 3.0)),
            allow_short=allow_short,
        )

    def donchian() -> pd.Series:
        return donchian_breakout_signals(
            frame,
            entry_window=int(params.get("dc_entry", 20)),
            exit_window=int(params.get("dc_exit", 10)),
            allow_short=allow_short,
        )

    def zscore() -> pd.Series:
        return zscore_mean_reversion_signals(
            close,
            window=int(params.get("z_window", 20)),
            entry_z=float(params.get("z_entry", 2.0)),
            exit_z=float(params.get("z_exit", 0.5)),
            allow_short=allow_short,
        )

    def rsi2() -> pd.Series:
        return rsi2_pullback_signals(
            close,
            oversold=float(params.get("rsi_oversold", 10.0)),
            trend_window=int(params.get("rsi_trend", 200)),
        )

    builders = {
        "Supertrend": supertrend,
        "Donchian breakout": donchian,
        "Z-score mean reversion": zscore,
        "RSI(2) pullback": rsi2,
    }
    if strategy == "Ensemble (all four)":
        return ensemble_vote(
            {name: build() for name, build in builders.items()},
            threshold=float(params.get("vote_threshold", 0.5)),
        )
    if strategy not in builders:
        raise ValueError(f"Unknown strategy: {strategy}")
    return builders[strategy]()


def run_strategy_lab(
    frame: pd.DataFrame,
    strategy: str,
    *,
    capital: float = 100_000.0,
    cost_bps: float = 10.0,
    cost_model: IndiaEquityCostModel | None = None,
    allow_short: bool = False,
    target_volatility: float | None = None,
    max_leverage: float = 1.0,
    params: dict[str, float] | None = None,
    regime: pd.Series | None = None,
) -> StrategyLabResult:
    """Build the signal, optionally volatility-target it, and backtest it.

    A ``cost_model`` (see ``india_cost_model``) replaces the flat ``cost_bps`` when given.
    ``regime`` is a boolean gate (see ``regime_filter``): positions are flat where it is False.

    ``target_volatility`` (annualised, e.g. 0.15) scales positions down in turbulent
    markets; ``None`` keeps the raw -1/0/+1 positions.
    """
    data = normalise_price_frame(frame)
    signals = build_signals(data, strategy, allow_short=allow_short, params=params)
    if regime is not None:
        signals = apply_regime_gate(signals, regime)
    if target_volatility is not None:
        signals = signals * volatility_target_scale(
            data["Close"], target_volatility=target_volatility, max_leverage=max_leverage
        )
    curve, metrics = run_backtest(
        data["Close"],
        signals,
        initial_capital=capital,
        cost_bps=cost_bps,
        cost_model=cost_model,
    )
    return StrategyLabResult(strategy, signals, curve, metrics)


def compare_strategies(
    frame: pd.DataFrame,
    *,
    capital: float = 100_000.0,
    cost_bps: float = 10.0,
    cost_model: IndiaEquityCostModel | None = None,
    allow_short: bool = False,
) -> pd.DataFrame:
    """One row of headline metrics per strategy, for a side-by-side table."""
    rows = []
    for name in STRATEGIES:
        try:
            result = run_strategy_lab(
                frame,
                name,
                capital=capital,
                cost_bps=cost_bps,
                cost_model=cost_model,
                allow_short=allow_short,
            )
        except ValueError:
            continue
        m = result.metrics
        rows.append(
            {
                "Strategy": name,
                "Total return": m.total_return,
                "CAGR": m.cagr,
                "Max drawdown": m.max_drawdown,
                "Sharpe": m.sharpe_ratio,
                "Trades": m.trade_count,
                "Win rate": m.win_rate,
                "Buy & hold": m.buy_hold_return,
            }
        )
    return pd.DataFrame(rows)
