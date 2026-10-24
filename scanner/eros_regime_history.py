"""Session-scoped EROS trend regime history helpers."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

HISTORY_LIMIT = 120

REQUIRED_COLUMNS = {
    "Timestamp",
    "Signals",
    "Rising Confirmed",
    "Falling Confirmed",
    "Mixed",
    "Insufficient Data",
    "High Confidence",
    "Moderate Confidence",
    "Low Confidence",
    "Rising Breadth %",
    "Falling Breadth %",
    "Average Trend Confidence %",
    "Regime",
}


def append_eros_regime_snapshot(
    history: pd.DataFrame | None,
    timestamp: datetime,
    regime: pd.DataFrame | None,
) -> pd.DataFrame:
    """Append one current EROS regime snapshot to a bounded session history."""
    if regime is None or regime.empty:
        return history.copy() if history is not None else pd.DataFrame()

    regime_columns = REQUIRED_COLUMNS - {"Timestamp"}
    if not regime_columns.issubset(regime.columns):
        return history.copy() if history is not None else pd.DataFrame()

    row = regime.iloc[[0]].copy()
    row.insert(0, "Timestamp", pd.Timestamp(timestamp))

    previous = history.copy() if history is not None and not history.empty else pd.DataFrame()
    if not previous.empty:
        if "Timestamp" not in previous.columns:
            previous = pd.DataFrame()
        else:
            previous["Timestamp"] = pd.to_datetime(previous["Timestamp"], errors="coerce")
            previous = previous.dropna(subset=["Timestamp"])

    combined = pd.concat([previous, row], ignore_index=True)
    combined["Timestamp"] = pd.to_datetime(combined["Timestamp"], errors="coerce")
    combined = combined.dropna(subset=["Timestamp"])
    combined = combined.sort_values("Timestamp").drop_duplicates(subset=["Timestamp"], keep="last")
    return combined.tail(HISTORY_LIMIT).reset_index(drop=True)


def summarize_eros_regime_history(history: pd.DataFrame | None) -> pd.DataFrame:
    """Describe the latest regime, its prior regime, and breadth change."""
    if history is None or history.empty:
        return pd.DataFrame()

    if not REQUIRED_COLUMNS.issubset(history.columns):
        return pd.DataFrame()

    frame = history.copy()
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    frame = frame.dropna(subset=["Timestamp"]).sort_values("Timestamp")
    if frame.empty:
        return pd.DataFrame()

    latest = frame.iloc[-1]
    previous = frame.iloc[-2] if len(frame) >= 2 else None

    latest_regime = str(latest["Regime"])
    previous_regime = str(previous["Regime"]) if previous is not None else "NO PRIOR SNAPSHOT"
    transition = "UNCHANGED"
    if previous is None:
        transition = "INITIAL"
    elif latest_regime != previous_regime:
        transition = f"{previous_regime} → {latest_regime}"

    rising_delta = (
        round(float(latest["Rising Breadth %"]) - float(previous["Rising Breadth %"]), 2)
        if previous is not None
        else None
    )
    falling_delta = (
        round(float(latest["Falling Breadth %"]) - float(previous["Falling Breadth %"]), 2)
        if previous is not None
        else None
    )

    return pd.DataFrame(
        [
            {
                "Latest Timestamp": latest["Timestamp"],
                "Current Regime": latest_regime,
                "Previous Regime": previous_regime,
                "Regime Transition": transition,
                "Rising Breadth %": float(latest["Rising Breadth %"]),
                "Falling Breadth %": float(latest["Falling Breadth %"]),
                "Rising Breadth Δ": rising_delta,
                "Falling Breadth Δ": falling_delta,
                "Average Trend Confidence %": float(latest["Average Trend Confidence %"]),
                "Snapshots": len(frame),
            }
        ]
    )
