"""Tests for market-session status helpers."""

# ruff: isort: skip_file
# fmt: off

from datetime import datetime
from zoneinfo import ZoneInfo

from services.market_service import market_session_status

# fmt: on


IST = ZoneInfo("Asia/Kolkata")


def test_market_status_marks_previous_session_as_closed():
    now = datetime(2026, 9, 20, 12, 0, tzinfo=IST)
    status = market_session_status("2026-09-18T15:29:00+05:30", "intraday_1m", now)

    assert status["status"] == "MARKET CLOSED · WEEKEND"
    assert status["is_current_session"] is False


def test_market_status_marks_today_intraday_data():
    now = datetime(2026, 9, 18, 12, 0, tzinfo=IST)
    status = market_session_status("2026-09-18T11:59:00+05:30", "intraday_1m", now)

    assert status["status"] == "INTRADAY DATA · TODAY"
    assert status["is_current_session"] is True
    assert status["is_market_open"] is True


def test_market_status_marks_after_close_today_data():
    now = datetime(2026, 9, 18, 16, 0, tzinfo=IST)
    status = market_session_status("2026-09-18T15:29:00+05:30", "intraday_1m", now)

    assert status["status"] == "MARKET CLOSED · TODAY'S DATA"
    assert status["is_current_session"] is True
    assert status["is_market_open"] is False


def test_market_status_flags_stale_intraday_data_during_open_session():
    now = datetime(2026, 9, 18, 12, 0, tzinfo=IST)
    status = market_session_status("2026-09-18T11:40:00+05:30", "intraday_1m", now)

    assert status["status"] == "STALE INTRADAY DATA"
    assert status["is_current_session"] is False
    assert "more than 15 minutes old" in status["detail"]


def test_market_status_keeps_recent_intraday_data_current():
    now = datetime(2026, 9, 18, 12, 0, tzinfo=IST)
    status = market_session_status("2026-09-18T11:59:00+05:30", "intraday_1m", now)

    assert status["status"] == "INTRADAY DATA · TODAY"
    assert status["is_current_session"] is True


def test_market_status_rejects_future_dated_observation():
    now = datetime(2026, 9, 18, 12, 0, tzinfo=IST)
    status = market_session_status("2026-09-18T12:10:00+05:30", "intraday_1m", now)

    assert status["status"] == "FUTURE-DATED MARKET DATA"
    assert status["is_current_session"] is False
    assert "more than 5 minutes ahead" in status["detail"]


def test_market_status_allows_small_future_timestamp_skew():
    now = datetime(2026, 9, 18, 12, 0, tzinfo=IST)
    status = market_session_status("2026-09-18T12:03:00+05:30", "intraday_1m", now)

    assert status["status"] == "INTRADAY DATA · TODAY"
    assert status["is_current_session"] is True


def test_market_status_recalculates_when_current_time_changes():
    observed_at = "2026-09-18T11:59:00+05:30"
    during_session = datetime(2026, 9, 18, 12, 0, tzinfo=IST)
    after_close = datetime(2026, 9, 18, 16, 0, tzinfo=IST)

    open_status = market_session_status(observed_at, "intraday_1m", during_session)
    closed_status = market_session_status(observed_at, "intraday_1m", after_close)

    assert open_status["status"] == "INTRADAY DATA · TODAY"
    assert open_status["is_market_open"] is True
    assert closed_status["status"] == "MARKET CLOSED · TODAY'S DATA"
    assert closed_status["is_market_open"] is False


def test_market_status_does_not_present_daily_fallback_as_current_intraday_data():
    now = datetime(2026, 9, 18, 12, 0, tzinfo=IST)
    status = market_session_status("2026-09-18T09:15:00+05:30", "daily", now)

    assert status["status"] == "DAILY DATA ONLY · INTRADAY UNAVAILABLE"
    assert status["is_current_session"] is False
    assert status["is_market_open"] is True
    assert "must not be presented as a current intraday quote" in status["detail"]
