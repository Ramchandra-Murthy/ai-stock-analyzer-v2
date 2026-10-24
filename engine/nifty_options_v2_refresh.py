"""Refresh scheduling helpers for NIFTY Options V2 paper trading."""

# ruff: noqa: I001

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class MarketRefreshPolicy:
    """NSE market-hours refresh policy."""

    interval_seconds: int = 60
    open_time: time = time(9, 15)
    close_time: time = time(15, 30)

    def __post_init__(self) -> None:
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")


def is_market_hours(
    current: datetime,
    policy: MarketRefreshPolicy | None = None,
) -> bool:
    """Return whether a timestamp falls inside the configured weekday session."""
    selected = policy or MarketRefreshPolicy()
    localized = current.astimezone(IST)
    if localized.weekday() >= 5:
        return False
    current_time = localized.time().replace(microsecond=0)
    return selected.open_time <= current_time <= selected.close_time


def refresh_seconds(policy: MarketRefreshPolicy | None = None) -> int:
    """Return the configured refresh interval for the Streamlit fragment."""
    return (policy or MarketRefreshPolicy()).interval_seconds
