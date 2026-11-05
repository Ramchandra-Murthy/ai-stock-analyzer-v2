import pandas as pd

from algorithmic_trading.signal_backtest import generate_pipeline_signals


def _frame(periods: int = 90) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=periods, freq="D")
    close = pd.Series(range(100, 100 + periods), index=index, dtype=float)
    return pd.DataFrame(
        {
            "High": close + 1,
            "Low": close - 1,
            "Close": close,
        }
    )


def test_pipeline_signals_use_only_available_history() -> None:
    frame = _frame()
    benchmark = pd.Series(100.0, index=frame.index)

    signals = generate_pipeline_signals(frame, benchmark)

    assert signals.index.equals(frame.index)
    assert signals.iloc[:50].eq(0.0).all()
    assert signals.notna().all()


def test_pipeline_signals_are_bounded() -> None:
    frame = _frame()
    benchmark = pd.Series(100.0, index=frame.index)

    signals = generate_pipeline_signals(frame, benchmark)

    assert signals.isin([-1.0, 0.0, 1.0]).all()


def test_pipeline_signal_at_cutoff_is_unchanged_by_future_price_shock() -> None:
    frame = _frame()
    benchmark = pd.Series(100.0, index=frame.index)
    cutoff = 70

    baseline = generate_pipeline_signals(frame, benchmark)

    shocked_frame = frame.copy()
    future_index = shocked_frame.index[cutoff + 1 :]
    shocked_frame.loc[future_index, "High"] *= 8.0
    shocked_frame.loc[future_index, "Low"] *= 0.2
    shocked_frame.loc[future_index, "Close"] *= 5.0

    shocked_benchmark = benchmark.copy()
    shocked_benchmark.loc[future_index] *= 3.0
    shocked = generate_pipeline_signals(shocked_frame, shocked_benchmark)

    pd.testing.assert_series_equal(
        baseline.iloc[: cutoff + 1],
        shocked.iloc[: cutoff + 1],
    )
