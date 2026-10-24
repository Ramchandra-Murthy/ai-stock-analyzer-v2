"""Market-session status helpers for externally sourced observations."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)


def _coerce_ist(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize(IST)
        else:
            timestamp = timestamp.tz_convert(IST)
        return timestamp.to_pydatetime()
    except (TypeError, ValueError, OverflowError):
        return None


def describe_market_status(
    observed_at: Any,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Describe market/session state without claiming tick-level live data."""
    current = (now or datetime.now(IST)).astimezone(IST)
    observed = _coerce_ist(observed_at)

    if observed is None:
        return {
            "label": "⚪ DATA STATUS UNKNOWN",
            "message": "Observation time is unavailable; verify the provider timestamp.",
            "is_current_session": False,
            "age_minutes": None,
        }

    age_minutes = max(0.0, (current - observed).total_seconds() / 60.0)
    market_day = current.weekday() < 5
    market_open = MARKET_OPEN <= current.time() <= MARKET_CLOSE

    if market_day and market_open:
        if observed.date() == current.date() and age_minutes <= 15:
            label = "🟢 MARKET OPEN"
            message = (
                f"Latest available data: {observed:%d %b %Y, %H:%M IST}. "
                "Yahoo Finance data is not represented as exchange tick-live."
            )
        elif observed.date() == current.date():
            label = "🟡 MARKET OPEN — DATA DELAYED"
            message = (
                f"Latest available data: {observed:%d %b %Y, %H:%M IST} "
                f"({age_minutes:.0f} minutes old). Verify the provider timestamp."
            )
        else:
            label = "🟡 MARKET OPEN — PREVIOUS SESSION DATA"
            message = (
                f"Latest available session: {observed:%d %b %Y, %H:%M IST}. "
                "No current-session candle is available."
            )
    elif market_day and current.time() < MARKET_OPEN:
        label = "🟡 PRE-MARKET"
        message = (
            f"Latest available session: {observed:%d %b %Y, %H:%M IST}. "
            "Regular NSE/BSE cash-market hours begin at 09:15 IST."
        )
    else:
        label = "🔵 MARKET CLOSED"
        message = (
            f"Latest available session: {observed:%d %b %Y, %H:%M IST}. "
            "The dashboard is showing the latest available provider data."
        )

    return {
        "label": label,
        "message": message,
        "is_current_session": observed.date() == current.date(),
        "age_minutes": age_minutes,
        "observed_at": observed,
    }
