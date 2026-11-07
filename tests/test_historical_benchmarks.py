from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from ai_trading.historical_benchmarks import attach_historical_benchmarks


IST = ZoneInfo("Asia/Kolkata")


def _frame(values, dates):
    return pd.DataFrame(
        {"Close": values},
        index=pd.DatetimeIndex(dates).tz_localize(IST),
    )


def _history(timestamp=datetime(2026, 1, 5, 10, 0, tzinfo=IST)):
    return pd.DataFrame({
        "timestamp": [timestamp],
        "outcome_timestamp": [pd.Timestamp("2026-01-06", tz=IST)],
        "symbol": ["TCS"],
        "exchange": ["NSE"],
        "signal": ["LONG"],
        "horizon_days": [1],
    })


def test_intraday_signal_uses_previous_completed_close_and_exact_outcome_session():
    dates = ["2026-01-02", "2026-01-05", "2026-01-06"]
    frames = {
        "^NSEI": _frame([100.0, 103.0, 105.0], dates),
        "^CNXIT": _frame([200.0, 204.0, 210.0], dates),
    }

    result = attach_historical_benchmarks(_history(), frames)

    assert result.loc[0, "benchmark_return_pct"] == pytest.approx(5.0)
    assert result.loc[0, "benchmark_status"] == "matched_daily_close_proxy"
    assert result.loc[0, "sector"] == "IT services"
    assert result.loc[0, "sector_benchmark_name"] == "^CNXIT"
    assert result.loc[0, "sector_benchmark_return_pct"] == pytest.approx(5.0)


def test_after_close_signal_can_use_same_day_completed_close():
    dates = ["2026-01-02", "2026-01-05", "2026-01-06"]
    frames = {"^NSEI": _frame([100.0, 103.0, 105.0], dates)}
    history = _history(datetime(2026, 1, 5, 16, 0, tzinfo=IST))

    result = attach_historical_benchmarks(history, frames)

    assert result.loc[0, "benchmark_return_pct"] == pytest.approx((105 / 103 - 1) * 100)
    assert result.loc[0, "benchmark_status"] == "matched_daily_close_proxy"


def test_missing_exact_outcome_session_is_not_filled_from_an_earlier_close():
    frames = {"^NSEI": _frame([100.0, 103.0], ["2026-01-02", "2026-01-05"])}

    result = attach_historical_benchmarks(_history(), frames)

    assert pd.isna(result.loc[0, "benchmark_return_pct"])
    assert result.loc[0, "benchmark_status"] == "missing_outcome_benchmark_close"


def test_missing_benchmark_frame_is_explicit_and_does_not_fabricate_return():
    result = attach_historical_benchmarks(_history(), {})

    assert pd.isna(result.loc[0, "benchmark_return_pct"])
    assert result.loc[0, "benchmark_status"] == "benchmark_data_unavailable"
    assert result.loc[0, "sector_benchmark_status"] == "benchmark_data_unavailable"


def test_unmapped_sector_keeps_nifty_comparison_and_marks_sector_unavailable():
    history = _history().assign(symbol="UNKNOWNCO")
    frames = {"^NSEI": _frame(
        [100.0, 103.0, 105.0], ["2026-01-02", "2026-01-05", "2026-01-06"]
    )}

    result = attach_historical_benchmarks(history, frames)

    assert result.loc[0, "benchmark_return_pct"] == pytest.approx(5.0)
    assert result.loc[0, "sector"] == "Unmapped"
    assert pd.isna(result.loc[0, "sector_benchmark_return_pct"])
    assert result.loc[0, "sector_benchmark_status"] == "sector_unmapped"


def test_empty_history_returns_benchmark_columns():
    result = attach_historical_benchmarks(pd.DataFrame(), {})

    assert result.empty
    assert "benchmark_return_pct" in result.columns


def test_required_timestamps_are_validated():
    with pytest.raises(ValueError, match="outcome_timestamp"):
        attach_historical_benchmarks(pd.DataFrame({"symbol": ["TCS"]}), {})
