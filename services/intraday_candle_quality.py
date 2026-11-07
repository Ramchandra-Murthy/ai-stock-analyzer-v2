"""Quality diagnostics for intraday OHLCV candles and delayed quotes.

Missing minute bars are reported rather than filled because no-trade intervals and
provider omissions cannot be distinguished from OHLCV data alone.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from services.ohlcv_validation import validate_ohlcv_frame

IST = ZoneInfo("Asia/Kolkata")


def _as_ist(value: datetime) -> datetime:
    """Interpret naive timestamps as exchange-local and normalize aware values to IST."""
    if value.tzinfo is None:
        return value.replace(tzinfo=IST)
    return value.astimezone(IST)


def assess_intraday_candles(
    frame: pd.DataFrame | None,
    *,
    interval_minutes: int = 1,
    retrieved_at: datetime | None = None,
    max_quote_age_seconds: int = 180,
    market_session_active: bool = False,
) -> dict[str, Any]:
    """Report ordering, duplicates, gaps, and quote age without changing source data.

    Age-based blocking is disabled unless the caller confirms an active exchange
    session using its exchange calendar. This avoids false stale warnings after close,
    on weekends, and on holidays.
    """
    if interval_minutes < 1:
        raise ValueError("interval_minutes must be at least 1")
    if max_quote_age_seconds < 0:
        raise ValueError("max_quote_age_seconds cannot be negative")

    checked_at = _as_ist(retrieved_at or datetime.now(UTC))
    result: dict[str, Any] = {
        "status": "INVALID",
        "row_count": 0,
        "duplicate_timestamps": 0,
        "out_of_order": False,
        "missing_intervals": 0,
        "last_candle_at": None,
        "quote_age_seconds": None,
        "age_check_applied": bool(market_session_active),
        "delayed": False,
        "usable": False,
        "errors": [],
        "policy": "diagnostic_only_no_synthetic_candles",
    }
    if frame is None or frame.empty:
        result["errors"] = ["empty frame"]
        return result
    if not isinstance(frame.index, pd.DatetimeIndex):
        result["row_count"] = len(frame)
        result["errors"] = ["index must be a DatetimeIndex"]
        return result

    index = frame.index
    local_index = index.tz_localize(IST) if index.tz is None else index.tz_convert(IST)
    duplicate_count = int(local_index.duplicated(keep=False).sum())
    out_of_order = not local_index.is_monotonic_increasing
    unique_sorted = local_index.drop_duplicates().sort_values()

    interval = pd.Timedelta(minutes=interval_minutes)
    missing_intervals = 0
    if len(unique_sorted) > 1:
        deltas = unique_sorted.to_series().diff().dropna()
        missing_intervals = int(
            sum(max(0, int(delta // interval) - 1) for delta in deltas if delta > interval)
        )

    last_candle = local_index.max()
    quote_age = (checked_at - last_candle.to_pydatetime()).total_seconds()
    future_timestamp = quote_age < 0
    delayed = bool(market_session_active and quote_age > max_quote_age_seconds)

    _, validation_errors = validate_ohlcv_frame(frame)
    errors = list(validation_errors)
    if duplicate_count:
        errors.append("duplicate timestamps")
    if out_of_order:
        errors.append("timestamps are not in ascending order")
    if future_timestamp:
        errors.append("latest candle timestamp is in the future")
    if delayed:
        errors.append("latest candle exceeds the active-session age limit")

    errors = list(dict.fromkeys(errors))
    usable = not errors
    result.update(
        {
            "status": "VALID" if usable else "INVALID",
            "row_count": len(frame),
            "duplicate_timestamps": duplicate_count,
            "out_of_order": out_of_order,
            "missing_intervals": missing_intervals,
            "last_candle_at": last_candle.isoformat(),
            "quote_age_seconds": round(quote_age, 1),
            "delayed": delayed,
            "usable": usable,
            "errors": errors,
        }
    )
    return result
