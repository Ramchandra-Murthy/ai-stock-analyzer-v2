"""Helpers for controlled intraday dashboard auto-refresh."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)
DEFAULT_REFRESH_SECONDS = 300
ALLOWED_REFRESH_SECONDS = (60, 120, 300, 600)


def market_is_open(now: datetime | None = None) -> bool:
    """Return whether the NSE cash session is currently open on a weekday."""
    current = now.astimezone(INDIA_TIMEZONE) if now else datetime.now(INDIA_TIMEZONE)
    return current.weekday() < 5 and MARKET_OPEN <= current.time() < MARKET_CLOSE


def next_refresh_seconds(
    last_scan_at: datetime | None,
    interval_seconds: int = DEFAULT_REFRESH_SECONDS,
    now: datetime | None = None,
) -> int:
    """Return whole seconds until the next scheduled refresh."""
    current = now.astimezone(INDIA_TIMEZONE) if now else datetime.now(INDIA_TIMEZONE)
    if last_scan_at is None:
        return 0

    last = last_scan_at.astimezone(INDIA_TIMEZONE)
    elapsed = max(0, int((current - last).total_seconds()))
    return max(0, interval_seconds - elapsed)


def refresh_label(seconds: int) -> str:
    """Format a refresh countdown for compact dashboard display."""
    if seconds <= 0:
        return "refresh due"
    minutes, remaining = divmod(seconds, 60)
    return f"{minutes}m {remaining:02d}s" if minutes else f"{remaining}s"
