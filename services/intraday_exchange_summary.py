"""Descriptive exchange-level intraday scan summary helpers."""

# Ruff's isort check conflicts with Black for this module-level constant layout.
# Keep Black's required spacing and suppress only the conflicting I001 check.
# ruff: noqa: I001

from __future__ import annotations

from typing import Any

import pandas as pd

SUMMARY_COLUMNS = [
    "Exchange",
    "Candidates",
    "Average change %",
    "Average volume surge x",
    "Positive change %",
]


def exchange_summary(frame: pd.DataFrame | None) -> pd.DataFrame:
    """Return descriptive NSE/BSE metrics from the latest completed scan."""
    data = frame if frame is not None else pd.DataFrame()
    if data.empty or "Exchange" not in data.columns:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)

    rows: list[dict[str, Any]] = []
    for exchange, group in data.groupby("Exchange", dropna=True, sort=True):
        change = pd.to_numeric(group.get("5-min change %"), errors="coerce")
        volume = pd.to_numeric(group.get("Volume surge x"), errors="coerce")
        valid_change = change.dropna()
        rows.append(
            {
                "Exchange": str(exchange),
                "Candidates": int(len(group)),
                "Average change %": (
                    round(float(valid_change.mean()), 2) if not valid_change.empty else None
                ),
                "Average volume surge x": (
                    round(float(volume.mean()), 2) if volume.notna().any() else None
                ),
                "Positive change %": (
                    round(float((valid_change > 0).mean() * 100), 1)
                    if not valid_change.empty
                    else None
                ),
            }
        )

    return pd.DataFrame(rows, columns=SUMMARY_COLUMNS)
