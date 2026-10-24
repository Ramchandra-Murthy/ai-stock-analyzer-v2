"""Session-scoped price-jump history helpers."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

HISTORY_LIMIT = 300


def append_price_jump_snapshot(
    history: pd.DataFrame | None,
    timestamp: datetime,
    jumps: pd.DataFrame,
) -> pd.DataFrame:
    """Append qualifying price-jump rows to a bounded session history."""
    if jumps is None or jumps.empty:
        return history.copy() if history is not None else pd.DataFrame()

    required = {"Symbol", "Exchange"}
    if not required.issubset(jumps.columns):
        return history.copy() if history is not None else pd.DataFrame()

    change_columns = [column for column in jumps.columns if str(column).startswith("Change over ")]
    if not change_columns:
        return history.copy() if history is not None else pd.DataFrame()

    columns = ["Symbol", "Exchange"]
    for optional in [
        "Market-cap basket",
        "Last price",
        change_columns[0],
        "Latest bar volume",
        "Volume vs recent bars",
        "Latest candle (provider time)",
    ]:
        if optional in jumps.columns and optional not in columns:
            columns.append(optional)

    snapshot = jumps[columns].copy()
    snapshot.insert(0, "Timestamp", timestamp)
    snapshot[change_columns[0]] = pd.to_numeric(snapshot[change_columns[0]], errors="coerce")
    snapshot = snapshot.dropna(subset=[change_columns[0]])

    if snapshot.empty:
        return history.copy() if history is not None else pd.DataFrame()

    combined = (
        pd.concat([history, snapshot], ignore_index=True) if history is not None else snapshot
    )
    combined = combined.drop_duplicates(subset=["Timestamp", "Symbol", "Exchange"], keep="last")
    return combined.tail(HISTORY_LIMIT).reset_index(drop=True)
