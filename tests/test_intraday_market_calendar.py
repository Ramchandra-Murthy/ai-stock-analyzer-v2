from datetime import date, datetime
from zoneinfo import ZoneInfo


def test_october_2_2026_is_an_equity_market_holiday() -> None:
    from modules.intraday import _is_equity_market_holiday

    assert _is_equity_market_holiday(date(2026, 10, 2))


def test_market_is_closed_on_october_2_2026_during_regular_hours() -> None:
    from modules.intraday import _market_session_is_open

    ist = ZoneInfo("Asia/Kolkata")
    assert not _market_session_is_open(datetime(2026, 10, 2, 14, 30, tzinfo=ist))


def test_regular_weekday_session_remains_open() -> None:
    from modules.intraday import _market_session_is_open

    ist = ZoneInfo("Asia/Kolkata")
    assert _market_session_is_open(datetime(2026, 10, 1, 14, 30, tzinfo=ist))


def test_weekend_remains_closed() -> None:
    from modules.intraday import _market_session_is_open

    ist = ZoneInfo("Asia/Kolkata")
    assert not _market_session_is_open(datetime(2026, 10, 3, 14, 30, tzinfo=ist))
