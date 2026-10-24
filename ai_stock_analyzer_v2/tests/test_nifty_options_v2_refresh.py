from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from engine.nifty_options_v2_refresh import (
    MarketRefreshPolicy,
    is_market_hours,
    refresh_seconds,
)

IST = ZoneInfo("Asia/Kolkata")


def test_market_hours_cover_nse_session() -> None:
    assert is_market_hours(datetime(2026, 10, 5, 10, 0, tzinfo=IST))
    assert not is_market_hours(datetime(2026, 10, 5, 8, 59, tzinfo=IST))
    assert not is_market_hours(datetime(2026, 10, 5, 15, 31, tzinfo=IST))
    assert not is_market_hours(datetime(2026, 10, 4, 10, 0, tzinfo=IST))


def test_refresh_interval_defaults_to_one_minute() -> None:
    assert refresh_seconds() == 60


def test_refresh_policy_rejects_non_positive_interval() -> None:
    with pytest.raises(ValueError, match="interval_seconds"):
        MarketRefreshPolicy(interval_seconds=0)
