"""Tests for OHLC integrity and freshness validation."""

from datetime import UTC, datetime, timedelta

from modules.fibonacci_gann.market_data import OHLCBar, validate_ohlc_bars


def bar(minute: int, *, high: int = 12, low: int = 8) -> OHLCBar:
    return OHLCBar(
        datetime(2026, 10, 16, 10, minute, tzinfo=UTC),
        10,
        high,
        low,
        11,
    )


def test_valid_fresh_bars_pass() -> None:
    now = datetime(2026, 10, 16, 10, 2, tzinfo=UTC)
    result = validate_ohlc_bars([bar(0), bar(1)], now=now, max_age=timedelta(minutes=2))
    assert result.valid
    assert not result.reasons


def test_stale_bars_fail() -> None:
    now = datetime(2026, 10, 16, 10, 30, tzinfo=UTC)
    result = validate_ohlc_bars([bar(0)], now=now, max_age=timedelta(minutes=5))
    assert not result.valid
    assert any("stale" in reason for reason in result.reasons)


def test_future_latest_bar_fails() -> None:
    now = datetime(2026, 10, 16, 9, 59, tzinfo=UTC)
    result = validate_ohlc_bars([bar(0)], now=now)
    assert not result.valid
    assert any("future" in reason for reason in result.reasons)


def test_unordered_timestamps_fail() -> None:
    result = validate_ohlc_bars(
        [bar(1), bar(0)],
        now=datetime(2026, 10, 16, 10, 2, tzinfo=UTC),
    )
    assert not result.valid
    assert any("strictly increasing" in reason for reason in result.reasons)


def test_invalid_ohlc_geometry_fails() -> None:
    invalid = OHLCBar(bar(0).timestamp, 10, 10, 9, 11)
    result = validate_ohlc_bars([invalid], now=datetime(2026, 10, 16, 10, 1, tzinfo=UTC))
    assert not result.valid
    assert any("inconsistent OHLC" in reason for reason in result.reasons)


def test_empty_data_fails() -> None:
    result = validate_ohlc_bars([])
    assert not result.valid
    assert "no OHLC bars supplied" in result.reasons
