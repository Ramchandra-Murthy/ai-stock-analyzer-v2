"""Descriptive historical comparison for the current EROS regime."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {
    "Timestamp",
    "Regime",
    "Rising Breadth %",
    "Falling Breadth %",
    "Average Trend Confidence %",
}


def analyze_eros_regime_history_comparison(
    history: pd.DataFrame | None,
) -> pd.DataFrame:
    """Compare the latest regime snapshot with prior history."""
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

    latest = frame.iloc[-1]
    prior = frame.iloc[:-1]
    same_regime = prior[prior["Regime"].astype(str) == str(latest["Regime"])]

    def _average(column: str) -> float | None:
        if same_regime.empty:
            return None
        return round(float(same_regime[column].astype(float).mean()), 2)

    previous_snapshot = prior.iloc[-1] if not prior.empty else None

    return pd.DataFrame(
        [
            {
                "Latest Timestamp": latest["Timestamp"],
                "Current Regime": str(latest["Regime"]),
                "Previous Regime": (
                    str(previous_snapshot["Regime"])
                    if previous_snapshot is not None
                    else "NO PRIOR SNAPSHOT"
                ),
                "History Snapshots": len(frame),
                "Prior Same-Regime Snapshots": len(same_regime),
                "Current Rising Breadth %": float(latest["Rising Breadth %"]),
                "Historical Same-Regime Rising Breadth %": _average("Rising Breadth %"),
                "Current Falling Breadth %": float(latest["Falling Breadth %"]),
                "Historical Same-Regime Falling Breadth %": _average("Falling Breadth %"),
                "Current Trend Confidence %": float(latest["Average Trend Confidence %"]),
                "Historical Same-Regime Trend Confidence %": _average("Average Trend Confidence %"),
            }
        ]
    )
