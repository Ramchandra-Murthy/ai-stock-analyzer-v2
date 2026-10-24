"""Validation helpers for NIFTY Options Book V2 historical data."""

# ruff: noqa: I001

from __future__ import annotations

from datetime import date

import pandas as pd

REQUIRED_COLUMNS = ("observed_date", "expiry", "strike", "spot", "ltp")


def validate_options_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a normalized copy after validating required option observations."""
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")

    result = frame.loc[:, REQUIRED_COLUMNS].copy()
    result["observed_date"] = pd.to_datetime(result["observed_date"], errors="raise").dt.date
    result["expiry"] = pd.to_datetime(result["expiry"], errors="raise").dt.date

    for column in ("strike", "spot", "ltp"):
        result[column] = pd.to_numeric(result[column], errors="raise")

    if result[["strike", "spot"]].le(0).any().any():
        raise ValueError("strike and spot must be positive")
    if result["ltp"].lt(0).any():
        raise ValueError("ltp must be non-negative")
    if result["observed_date"].gt(result["expiry"]).any():
        raise ValueError("observed_date cannot be after expiry")

    duplicate_keys = result.duplicated(subset=["observed_date", "expiry", "strike"], keep=False)
    if duplicate_keys.any():
        raise ValueError("duplicate option observations are not allowed")

    return result


def validate_expiry(value: date) -> None:
    """Validate one expiry date."""
    if value.weekday() != 3:
        raise ValueError("NIFTY monthly expiry must be a Thursday")
