"""Session-scoped institutional momentum history helpers."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

HISTORY_LIMIT = 300


def append_momentum_snapshot(
    history: pd.DataFrame | None,
    timestamp: datetime,
    score: float,
    label: str,
) -> pd.DataFrame:
    """Append one score observation and keep the session history bounded."""
    row = pd.DataFrame([{"Timestamp": timestamp, "Score": float(score), "Label": str(label)}])
    if history is None or history.empty:
        return row

    combined = pd.concat([history, row], ignore_index=True)
    combined["Timestamp"] = pd.to_datetime(combined["Timestamp"], errors="coerce")
    combined["Score"] = pd.to_numeric(combined["Score"], errors="coerce")
    combined = combined.dropna(subset=["Timestamp", "Score"])
    combined = combined.drop_duplicates(subset=["Timestamp"], keep="last")
    return combined.tail(HISTORY_LIMIT).reset_index(drop=True)
