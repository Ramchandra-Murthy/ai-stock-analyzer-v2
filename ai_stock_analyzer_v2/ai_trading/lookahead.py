"""Book-aligned lookahead-bias forensic checks for research datasets."""

from __future__ import annotations

import pandas as pd


def _coerce_timestamps(values: pd.Series, *, name: str) -> pd.Series:
    timestamps = pd.to_datetime(values, errors="coerce")
    if timestamps.isna().any():
        raise ValueError(f"{name} contains invalid or missing timestamps")
    return timestamps.reset_index(drop=True)


def assert_no_future_observations(
    frame: pd.DataFrame,
    *,
    timestamp_column: str,
    as_of: str | pd.Timestamp,
) -> None:
    """Raise when a dataset contains observations after its decision timestamp."""
    if timestamp_column not in frame.columns:
        raise KeyError(f"missing timestamp column: {timestamp_column}")

    timestamps = _coerce_timestamps(frame[timestamp_column], name=timestamp_column)
    cutoff = pd.Timestamp(as_of)

    try:
        future_count = int((timestamps > cutoff).sum())
    except TypeError as exc:
        raise ValueError("as_of must use a compatible timestamp timezone") from exc

    if future_count:
        raise ValueError(
            f"lookahead detected: {future_count} observations occur after the as_of timestamp"
        )


def assert_no_timestamp_lookahead(
    source_timestamps: pd.Series,
    decision_timestamps: pd.Series,
    *,
    source_name: str = "source timestamps",
) -> None:
    """Raise when any source observation occurs after its decision timestamp."""
    if len(source_timestamps) != len(decision_timestamps):
        raise ValueError("source and decision timestamp series must have the same length")

    source = _coerce_timestamps(source_timestamps, name=source_name)
    decisions = _coerce_timestamps(decision_timestamps, name="decision timestamps")

    try:
        future_count = int((source > decisions).sum())
    except TypeError as exc:
        raise ValueError("source and decision timestamps must use compatible timezones") from exc

    if future_count:
        raise ValueError(
            f"lookahead detected: {future_count} {source_name} occur after their "
            "decision timestamps"
        )


def assert_no_label_lookahead(
    label_end_timestamps: pd.Series,
    decision_timestamps: pd.Series,
) -> None:
    """Raise when a training label is not fully known at the decision timestamp."""
    assert_no_timestamp_lookahead(
        label_end_timestamps,
        decision_timestamps,
        source_name="label end timestamps",
    )
