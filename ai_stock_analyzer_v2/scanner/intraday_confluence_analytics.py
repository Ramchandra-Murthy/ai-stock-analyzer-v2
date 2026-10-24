"""Intraday signal confluence analytics helpers."""

from __future__ import annotations

import pandas as pd


def summarize_confluence_history(history: pd.DataFrame | None) -> pd.DataFrame:
    """Summarize repeated high-confluence observations by symbol and exchange."""
    if history is None or history.empty:
        return pd.DataFrame()

    required = {"Timestamp", "Symbol", "Exchange", "Confluence Score"}
    if not required.issubset(history.columns):
        return pd.DataFrame()

    frame = history.copy()
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    frame["Confluence Score"] = pd.to_numeric(frame["Confluence Score"], errors="coerce")
    frame = frame.dropna(subset=["Timestamp", "Confluence Score"])
    if frame.empty:
        return pd.DataFrame()

    summary = (
        frame.groupby(["Symbol", "Exchange"], as_index=False)
        .agg(
            Observations=("Symbol", "size"),
            Average_Score=("Confluence Score", "mean"),
            Peak_Score=("Confluence Score", "max"),
            First_Seen=("Timestamp", "min"),
            Last_Seen=("Timestamp", "max"),
        )
        .sort_values(
            ["Observations", "Average_Score", "Peak_Score"],
            ascending=[False, False, False],
        )
        .reset_index(drop=True)
    )
    summary["Persistence"] = pd.cut(
        summary["Observations"],
        bins=[0, 1, 2, 4, float("inf")],
        labels=["ONE", "REPEATED", "PERSISTENT", "HIGH PERSISTENCE"],
    )
    return summary
