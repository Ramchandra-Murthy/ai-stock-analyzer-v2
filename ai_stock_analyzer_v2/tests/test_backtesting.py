import numpy as np
import pandas as pd

from modules.backtesting import _run_backtest


def _history():
    index = pd.date_range("2026-01-01", periods=6, freq="D")
    close = pd.Series([100, 102, 101, 105, 104, 108], index=index)
    return pd.DataFrame(
        {
            "Close": close,
            "EMA20": close.ewm(span=20, adjust=False).mean(),
            "EMA50": close.ewm(span=50, adjust=False).mean(),
        }
    )


def test_backtest_returns_finite_equity_series():
    results, _ = _run_backtest(_history(), initial_capital=100_000, cost_bps=10)

    assert results.index.is_monotonic_increasing
    assert results.index.is_unique
    assert results["strategy_equity"].notna().all()
    assert results["buy_hold_equity"].notna().all()
    assert np.isfinite(results["strategy_equity"]).all()
    assert np.isfinite(results["buy_hold_equity"]).all()


def test_backtest_rejects_empty_history():
    empty = pd.DataFrame(columns=["Close", "EMA20", "EMA50"])

    try:
        _run_backtest(empty, initial_capital=100_000, cost_bps=10)
    except ValueError as error:
        assert "Historical price data is unavailable" in str(error)
    else:
        raise AssertionError("Expected ValueError for empty history")
