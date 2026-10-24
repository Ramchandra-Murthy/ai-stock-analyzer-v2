"""EROS regime breadth and strength analytics helpers."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {
    "Timestamp",
    "Regime",
    "Rising Breadth %",
    "Average Trend Confidence %",
}


def analyze_eros_regime_breadth(history: pd.DataFrame | None) -> pd.DataFrame:
    """Summarize breadth and trend confidence for each aggregate regime."""
    if history is None or history.empty:
        return pd.DataFrame()
    if not REQUIRED_COLUMNS.issubset(history.columns):
        return pd.DataFrame()

    frame = history.loc[:, list(REQUIRED_COLUMNS)].copy()
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    frame["Rising Breadth %"] = pd.to_numeric(frame["Rising Breadth %"], errors="coerce")
    frame["Average Trend Confidence %"] = pd.to_numeric(
        frame["Average Trend Confidence %"], errors="coerce"
    )
    frame = frame.dropna(
        subset=["Timestamp", "Rising Breadth %", "Average Trend Confidence %"]
    ).sort_values("Timestamp")
    if frame.empty:
        return pd.DataFrame()

    frame["Regime"] = frame["Regime"].astype(str)
    grouped = frame.groupby("Regime", sort=False)
    result = grouped.agg(
        Snapshots=("Timestamp", "size"),
        Average_Rising_Breadth=("Rising Breadth %", "mean"),
        Minimum_Rising_Breadth=("Rising Breadth %", "min"),
        Maximum_Rising_Breadth=("Rising Breadth %", "max"),
        Average_Trend_Confidence=("Average Trend Confidence %", "mean"),
        Minimum_Trend_Confidence=("Average Trend Confidence %", "min"),
        Maximum_Trend_Confidence=("Average Trend Confidence %", "max"),
    ).reset_index()

    total = len(frame)
    result["Session Share %"] = result["Snapshots"].div(total).mul(100)
    result["Average Falling Breadth"] = 100.0 - result["Average_Rising_Breadth"]

    numeric_columns = [
        "Average_Rising_Breadth",
        "Minimum_Rising_Breadth",
        "Maximum_Rising_Breadth",
        "Average_Trend_Confidence",
        "Minimum_Trend_Confidence",
        "Maximum_Trend_Confidence",
        "Session Share %",
        "Average Falling Breadth",
    ]
    result[numeric_columns] = result[numeric_columns].round(2)

    return result[
        [
            "Regime",
            "Snapshots",
            "Session Share %",
            "Average_Rising_Breadth",
            "Average Falling Breadth",
            "Minimum_Rising_Breadth",
            "Maximum_Rising_Breadth",
            "Average_Trend_Confidence",
            "Minimum_Trend_Confidence",
            "Maximum_Trend_Confidence",
        ]
    ]
