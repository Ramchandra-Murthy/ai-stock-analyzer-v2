from datetime import UTC, datetime, timedelta

import pytest

from engine.nifty_options_v2_freshness import market_data_is_fresh


def test_market_data_is_fresh_within_default_window() -> None:
    fetched_at = datetime(2026, 10, 5, 9, 30, tzinfo=UTC)
    now = fetched_at + timedelta(minutes=1)
    assert market_data_is_fresh(fetched_at, now=now)


def test_market_data_is_stale_after_default_window() -> None:
    fetched_at = datetime(2026, 10, 5, 9, 30, tzinfo=UTC)
    now = fetched_at + timedelta(minutes=3)
    assert not market_data_is_fresh(fetched_at, now=now)


def test_market_data_rejects_naive_timestamps() -> None:
    fetched_at = datetime(2026, 10, 5, 9, 30)
    now = datetime(2026, 10, 5, 9, 31, tzinfo=UTC)
    with pytest.raises(ValueError, match="timezone-aware"):
        market_data_is_fresh(fetched_at, now=now)
