"""Helpers for recording intraday scan health history."""

# fmt: off
from __future__ import annotations  # noqa: I001

from datetime import datetime
from typing import Any

import pandas as pd


HEALTH_COLUMNS = [
    "Observed at",
    "Status",
    "Message",
    "Age minutes",
    "Candidates",
]


def record_health_observation(
    history: list[dict[str, Any]],
    health: dict[str, Any],
    observed_at: datetime,
) -> list[dict[str, Any]]:
    """Append one descriptive health observation to the session history."""
    record = {
        "Observed at": observed_at,
        "Status": str(health.get("status", "UNKNOWN")),
        "Message": str(health.get("message", "")),
        "Age minutes": health.get("age_minutes"),
        "Candidates": health.get("candidates"),
    }
    return [record, *history]


def health_history_frame(history: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert health observations into a stable display DataFrame."""
    if not history:
        return pd.DataFrame(columns=HEALTH_COLUMNS)

    frame = pd.DataFrame(history)
    for column in HEALTH_COLUMNS:
        if column not in frame.columns:
            frame[column] = None

    frame["Observed at"] = pd.to_datetime(frame["Observed at"], errors="coerce")
    return frame[HEALTH_COLUMNS].reset_index(drop=True)

# fmt: on
