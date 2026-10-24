from datetime import UTC, datetime

from engine.nifty_options_v2_market_session import market_session_ready


def test_market_session_is_ready_during_nse_hours() -> None:
    now = datetime(2026, 10, 5, 6, 0, tzinfo=UTC)
    assert market_session_ready(now)


def test_market_session_is_not_ready_before_open() -> None:
    now = datetime(2026, 10, 5, 3, 30, tzinfo=UTC)
    assert not market_session_ready(now)


def test_market_session_is_not_ready_after_close() -> None:
    now = datetime(2026, 10, 5, 10, 0, tzinfo=UTC)
    assert not market_session_ready(now)


def test_market_session_is_not_ready_on_weekend() -> None:
    now = datetime(2026, 10, 4, 6, 0, tzinfo=UTC)
    assert not market_session_ready(now)
