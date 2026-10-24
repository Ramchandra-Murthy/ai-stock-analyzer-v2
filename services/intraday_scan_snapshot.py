"""Session-local scan snapshot history helpers."""

# ruff: isort: skip_file

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

# fmt: off


SNAPSHOT_COLUMNS = [
    "Timestamp",
    "Candidates",
    "Average change %",
    "Average volume surge x",
    "Exchanges",
    "Market-cap baskets",
    "Top symbols",
]


def record_scan_snapshot(
    history: list[dict[str, Any]] | None,
    frame: pd.DataFrame | None,
    timestamp: datetime,
    *,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """Record descriptive aggregate metrics for one completed scan."""
    data = frame if frame is not None else pd.DataFrame()
    if data.empty:
        return list(history or [])
    change = pd.to_numeric(data.get("5-min change %"), errors="coerce")
    volume = pd.to_numeric(data.get("Volume surge x"), errors="coerce")
    symbols = data.get("Symbol", pd.Series(dtype=str)).dropna().astype(str).head(top_n)
    exchanges = data.get("Exchange", pd.Series(dtype=str)).dropna().astype(str).unique().tolist()
    baskets = (
        data.get("Market-cap basket", pd.Series(dtype=str))
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    record = {
        "Timestamp": timestamp.isoformat(),
        "Candidates": int(len(data)),
        "Average change %": round(float(change.mean()), 2) if change.notna().any() else None,
        "Average volume surge x": round(float(volume.mean()), 2) if volume.notna().any() else None,
        "Exchanges": ", ".join(exchanges),
        "Market-cap baskets": ", ".join(baskets),
        "Top symbols": ", ".join(symbols.tolist()),
    }
    return list(history or []) + [record]


def snapshot_frame(history: list[dict[str, Any]] | None) -> pd.DataFrame:
    """Return scan snapshots in stable display order."""
    frame = pd.DataFrame(history or [])
    if frame.empty:
        return pd.DataFrame(columns=SNAPSHOT_COLUMNS)
    return frame.reindex(columns=SNAPSHOT_COLUMNS)
