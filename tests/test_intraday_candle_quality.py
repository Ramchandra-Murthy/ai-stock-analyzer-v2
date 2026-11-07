from datetime import datetime

import pandas as pd

from services.intraday_candle_quality import assess_intraday_candles


def _candles(times: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0] * len(times),
            "High": [101.0] * len(times),
            "Low": [99.0] * len(times),
            "Close": [100.5] * len(times),
            "Volume": [1000] * len(times),
        },
        index=pd.to_datetime(times),
    )


def test_valid_one_minute_candles_have_no_gaps() -> None:
    result = assess_intraday_candles(
        _candles(["2026-11-06 09:15", "2026-11-06 09:16"]),
        retrieved_at=datetime.fromisoformat("2026-11-06T09:16:30+05:30"),
        market_session_active=True,
    )

    assert result["status"] == "VALID"
    assert result["usable"] is True
    assert result["missing_intervals"] == 0
    assert result["quote_age_seconds"] == 30.0


def test_duplicate_timestamps_are_rejected() -> None:
    result = assess_intraday_candles(
        _candles(["2026-11-06 09:15", "2026-11-06 09:15"]),
    )

    assert result["usable"] is False
    assert result["duplicate_timestamps"] == 2
    assert "duplicate timestamps" in result["errors"]


def test_out_of_order_timestamps_are_rejected_without_reordering_source() -> None:
    frame = _candles(["2026-11-06 09:16", "2026-11-06 09:15"])
    original = frame.index.copy()

    result = assess_intraday_candles(frame)

    assert result["out_of_order"] is True
    assert result["usable"] is False
    assert frame.index.equals(original)


def test_missing_minute_intervals_are_reported_not_fabricated() -> None:
    result = assess_intraday_candles(
        _candles(["2026-11-06 09:15", "2026-11-06 09:18"]),
    )

    assert result["missing_intervals"] == 2
    assert result["row_count"] == 2
    assert result["usable"] is True


def test_delayed_quote_blocks_only_when_caller_confirms_active_session() -> None:
    frame = _candles(["2026-11-06 09:15"])
    checked_at = datetime.fromisoformat("2026-11-06T09:20:00+05:30")

    active = assess_intraday_candles(
        frame,
        retrieved_at=checked_at,
        max_quote_age_seconds=180,
        market_session_active=True,
    )
    closed = assess_intraday_candles(
        frame,
        retrieved_at=checked_at,
        max_quote_age_seconds=180,
        market_session_active=False,
    )

    assert active["delayed"] is True
    assert active["usable"] is False
    assert closed["age_check_applied"] is False
    assert closed["delayed"] is False
    assert closed["usable"] is True


def test_future_candle_timestamp_is_rejected() -> None:
    result = assess_intraday_candles(
        _candles(["2026-11-06 09:17"]),
        retrieved_at=datetime.fromisoformat("2026-11-06T09:16:00+05:30"),
    )

    assert result["usable"] is False
    assert "latest candle timestamp is in the future" in result["errors"]


def test_invalid_index_and_empty_input_are_reported() -> None:
    assert assess_intraday_candles(pd.DataFrame())["errors"] == ["empty frame"]
    frame = pd.DataFrame({"Open": [1]})
    assert assess_intraday_candles(frame)["errors"] == ["index must be a DatetimeIndex"]
