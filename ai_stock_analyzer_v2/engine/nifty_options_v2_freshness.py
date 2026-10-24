"""Freshness checks for NIFTY Options V2 paper market data."""

# ruff: noqa: I001

from __future__ import annotations

from datetime import datetime, timedelta

DEFAULT_MAX_AGE = timedelta(minutes=2)


def market_data_is_fresh(
    fetched_at: datetime,
    *,
    now: datetime,
    max_age: timedelta = DEFAULT_MAX_AGE,
) -> bool:
    """Return whether dashboard-fetched market data is within the safety age limit."""
    if fetched_at.tzinfo is None or now.tzinfo is None:
        raise ValueError("fetched_at and now must be timezone-aware")
    age = now - fetched_at
    return timedelta(0) <= age <= max_age
