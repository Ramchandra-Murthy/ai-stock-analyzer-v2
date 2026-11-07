"""Tests for controlled intraday dashboard auto-refresh."""

from datetime import datetime

from services.intraday_auto_refresh import (
    market_is_open,
    next_refresh_seconds,
    refresh_label,
)


def test_market_is_open_during_weekday_session():
    now = datetime.fromisoformat("2026-09-21T12:00:00+05:30")
    assert market_is_open(now) is True


def test_market_is_closed_on_weekend():
    now = datetime.fromisoformat("2026-09-20T12:00:00+05:30")
    assert market_is_open(now) is False


def test_next_refresh_counts_down_from_last_scan():
    last = datetime.fromisoformat("2026-09-21T12:00:00+05:30")
    now = datetime.fromisoformat("2026-09-21T12:03:30+05:30")
    assert next_refresh_seconds(last, 300, now) == 90


def test_refresh_label_formats_minutes_and_seconds():
    assert refresh_label(90) == "1m 30s"
    assert refresh_label(0) == "refresh due"


def test_live_board_fetches_during_market_session():
    from services.intraday_auto_refresh import should_fetch_live_board

    assert should_fetch_live_board(market_session_active=True, has_snapshot=True) is True


def test_closed_market_reuses_existing_snapshot():
    from services.intraday_auto_refresh import should_fetch_live_board

    assert should_fetch_live_board(market_session_active=False, has_snapshot=True) is False


def test_closed_market_fetches_once_when_no_snapshot_exists():
    from services.intraday_auto_refresh import should_fetch_live_board

    assert should_fetch_live_board(market_session_active=False, has_snapshot=False) is True
