"""Session-scoped EROS fusion history helpers."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

HISTORY_LIMIT = 300


def append_eros_fusion_snapshot(
    history: pd.DataFrame | None,
    timestamp: datetime,
    fusion: pd.DataFrame,
) -> pd.DataFrame:
    """Append current EROS fusion rows to a bounded session history."""
    if fusion is None or fusion.empty:
        return history.copy() if history is not None else pd.DataFrame()

    required = {"Symbol", "Exchange", "Fusion Score"}
    if not required.issubset(fusion.columns):
        return history.copy() if history is not None else pd.DataFrame()

    columns = ["Symbol", "Exchange", "Fusion Score"]
    for optional in [
        "Fusion Coverage",
        "Confluence Component",
        "Persistence Component",
        "Price Jump Component",
        "Institutional Component",
    ]:
        if optional in fusion.columns:
            columns.append(optional)

    snapshot = fusion[columns].copy()
    snapshot.insert(0, "Timestamp", timestamp)
    snapshot["Fusion Score"] = pd.to_numeric(snapshot["Fusion Score"], errors="coerce")
    snapshot = snapshot.dropna(subset=["Fusion Score"])
    if snapshot.empty:
        return history.copy() if history is not None else pd.DataFrame()

    combined = (
        pd.concat([history, snapshot], ignore_index=True) if history is not None else snapshot
    )
    combined = combined.drop_duplicates(
        subset=["Timestamp", "Symbol", "Exchange"],
        keep="last",
    )
    return combined.tail(HISTORY_LIMIT).reset_index(drop=True)
