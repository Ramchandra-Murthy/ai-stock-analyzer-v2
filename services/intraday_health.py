"""Helpers for intraday dashboard health and data-freshness checks."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

REQUIRED_RESULT_COLUMNS = ("Symbol", "Price")
DEFAULT_MAX_AGE_MINUTES = 10


def assess_scan_health(
    results: pd.DataFrame | None,
    observed_at: datetime | None,
    *,
    max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES,
) -> dict[str, Any]:
    """Return descriptive health checks for the latest intraday scan."""
    if results is None:
        return _status("NO_SCAN", "No intraday scan has been completed yet.")

    if results.empty:
        return _status("EMPTY", "The latest scan returned no candidates.")

    missing = [column for column in REQUIRED_RESULT_COLUMNS if column not in results.columns]
    if missing:
        return _status(
            "INVALID_SCHEMA",
            f"Latest scan is missing required columns: {', '.join(missing)}.",
        )

    if observed_at is None:
        return _status("NO_TIMESTAMP", "The latest scan has no observation timestamp.")

    age_minutes = max(
        0.0,
        (datetime.now(tz=observed_at.tzinfo) - observed_at).total_seconds() / 60,
    )
    if age_minutes > max_age_minutes:
        return _status(
            "STALE",
            f"Latest scan is {age_minutes:.1f} minutes old.",
            age_minutes=round(age_minutes, 1),
        )

    return _status(
        "HEALTHY",
        f"Latest scan is {age_minutes:.1f} minutes old.",
        age_minutes=round(age_minutes, 1),
        candidates=len(results),
    )


def _status(status: str, message: str, **extra: Any) -> dict[str, Any]:
    """Build a stable health-check payload."""
    return {"status": status, "message": message, **extra}
