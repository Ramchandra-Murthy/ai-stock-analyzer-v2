"""Book-aligned point-in-time guards for historical market datasets."""

from __future__ import annotations

import pandas as pd


def validate_timestamp_column(
    frame: pd.DataFrame,
    *,
    timestamp_column: str,
) -> pd.Series:
    """Validate and return a chronological timestamp series."""
    if timestamp_column not in frame.columns:
        raise KeyError(f"missing timestamp column: {timestamp_column}")

    timestamps = pd.to_datetime(frame[timestamp_column], errors="coerce")
    if timestamps.isna().any():
        raise ValueError("timestamp column contains invalid or missing values")
    if not timestamps.is_monotonic_increasing:
        raise ValueError("timestamp column must be sorted in ascending order")

    return timestamps


def point_in_time_slice(
    frame: pd.DataFrame,
    *,
    timestamp_column: str,
    as_of: str | pd.Timestamp,
) -> pd.DataFrame:
    """Return only observations that were available at the requested timestamp."""
    timestamps = validate_timestamp_column(frame, timestamp_column=timestamp_column)
    cutoff = pd.Timestamp(as_of)

    try:
        mask = timestamps <= cutoff
    except TypeError as exc:
        raise ValueError("as_of must use a compatible timestamp timezone") from exc

    return frame.loc[mask].copy()
