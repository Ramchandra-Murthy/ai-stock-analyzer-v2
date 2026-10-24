"""Session-scoped intraday signal confluence history helpers."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

HISTORY_LIMIT = 300


def append_confluence_snapshot(
    history: pd.DataFrame | None,
    timestamp: datetime,
    board: pd.DataFrame,
    min_score: float = 75.0,
) -> pd.DataFrame:
    """Append high-confluence rows to a bounded session history."""
    if board is None or board.empty:
        return history.copy() if history is not None else pd.DataFrame()

    required = {"Symbol", "Exchange", "Confluence Score", "Confluence"}
    if not required.issubset(board.columns):
        return history.copy() if history is not None else pd.DataFrame()

    rows = board[pd.to_numeric(board["Confluence Score"], errors="coerce") >= min_score].copy()
    if rows.empty:
        return history.copy() if history is not None else pd.DataFrame()

    columns = ["Symbol", "Exchange", "Confluence Score", "Confluence"]
    for optional in ["Sector", "Price", "3-min change %", "Relative Strength"]:
        if optional in rows.columns:
            columns.append(optional)

    snapshot = rows[columns].copy()
    snapshot.insert(0, "Timestamp", timestamp)
    snapshot["Confluence Score"] = pd.to_numeric(snapshot["Confluence Score"], errors="coerce")
    snapshot["Confluence"] = snapshot["Confluence"].astype(str)

    combined = (
        pd.concat([history, snapshot], ignore_index=True) if history is not None else snapshot
    )
    combined = combined.drop_duplicates(subset=["Timestamp", "Symbol", "Exchange"], keep="last")
    return combined.tail(HISTORY_LIMIT).reset_index(drop=True)
