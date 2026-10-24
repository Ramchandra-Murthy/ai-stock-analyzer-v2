"""Descriptive distribution analytics for EROS regime history."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {
    "Timestamp",
    "Regime",
    "Rising Breadth %",
    "Falling Breadth %",
    "Average Trend Confidence %",
}


def analyze_eros_regime_distribution(
    history: pd.DataFrame | None,
) -> pd.DataFrame:
    """Summarize frequency and descriptive metrics for each observed regime."""
    if history is None or history.empty:
        return pd.DataFrame()
    if not REQUIRED_COLUMNS.issubset(history.columns):
        return pd.DataFrame()

    frame = history.loc[:, list(REQUIRED_COLUMNS)].copy()
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    frame = frame.dropna(subset=["Timestamp"]).sort_values("Timestamp")
    frame = frame.drop_duplicates(subset=["Timestamp"], keep="last")
    if frame.empty:
        return pd.DataFrame()

    frame["Regime"] = frame["Regime"].astype(str)
    frame = frame[frame["Regime"].str.strip().ne("")]
    if frame.empty:
        return pd.DataFrame()

    total = len(frame)
    rows: list[dict[str, object]] = []
    for regime, group in frame.groupby("Regime", sort=False):
        rows.append(
            {
                "Regime": regime,
                "Snapshots": len(group),
                "Share of History %": round(len(group) / total * 100, 2),
                "First Observed": group["Timestamp"].min(),
                "Last Observed": group["Timestamp"].max(),
                "Average Rising Breadth %": round(
                    float(group["Rising Breadth %"].astype(float).mean()), 2
                ),
                "Average Falling Breadth %": round(
                    float(group["Falling Breadth %"].astype(float).mean()), 2
                ),
                "Average Trend Confidence %": round(
                    float(group["Average Trend Confidence %"].astype(float).mean()),
                    2,
                ),
            }
        )

    return pd.DataFrame(rows)
