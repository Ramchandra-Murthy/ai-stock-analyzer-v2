"""Historical backtest adapter for the NSE/BSE algorithmic signal pipeline."""

from __future__ import annotations

import pandas as pd

from algorithmic_trading.backtester import BacktestMetrics, run_backtest
from algorithmic_trading.regime_engine import classify_regime, regime_score
from algorithmic_trading.relative_strength import relative_return
from algorithmic_trading.signal_engine import compose_signal
from algorithmic_trading.trading_costs import IndiaEquityCostModel


def generate_pipeline_signals(
    frame: pd.DataFrame,
    benchmark: pd.Series,
    relative_periods: int = 20,
    minimum_history: int = 50,
) -> pd.Series:
    """Generate point-in-time signals without using future observations."""
    required = {"High", "Low", "Close"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    if minimum_history < max(relative_periods + 1, 50):
        minimum_history = max(relative_periods + 1, 50)

    close = pd.to_numeric(frame["Close"], errors="coerce")
    high = pd.to_numeric(frame["High"], errors="coerce")
    low = pd.to_numeric(frame["Low"], errors="coerce")
    data = pd.DataFrame({"High": high, "Low": low, "Close": close}).dropna()

    benchmark = pd.to_numeric(benchmark, errors="coerce").dropna()
    signals = pd.Series(0.0, index=data.index, name="signal")

    for index in range(minimum_history, len(data)):
        history = data.iloc[: index + 1]
        rs = relative_return(
            history["Close"],
            benchmark.reindex(history.index).dropna(),
            periods=relative_periods,
        )
        score = regime_score(history)
        regime = classify_regime(history)
        decision = compose_signal(
            regime=regime,
            regime_score=score,
            relative_return_pct=rs,
        )
        signals.iloc[index] = {
            "LONG": 1.0,
            "SHORT": -1.0,
            "FLAT": 0.0,
        }[decision.direction]

    return signals


def backtest_pipeline(
    frame: pd.DataFrame,
    benchmark: pd.Series,
    initial_capital: float = 100_000.0,
    cost_bps: float = 10.0,
    relative_periods: int = 20,
    cost_model: IndiaEquityCostModel | None = None,
) -> tuple[pd.DataFrame, BacktestMetrics]:
    """Backtest the same regime/relative-strength signal used by the scanner."""
    signals = generate_pipeline_signals(
        frame=frame,
        benchmark=benchmark,
        relative_periods=relative_periods,
    )
    prices = pd.to_numeric(frame["Close"], errors="coerce").reindex(signals.index)
    return run_backtest(
        prices=prices,
        signals=signals,
        initial_capital=initial_capital,
        cost_bps=cost_bps,
        cost_model=cost_model,
    )
