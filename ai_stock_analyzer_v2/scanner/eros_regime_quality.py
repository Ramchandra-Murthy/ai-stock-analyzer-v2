"""EROS regime quality dimension analytics helpers."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {
    "Timestamp",
    "Regime",
    "Rising Breadth %",
    "Falling Breadth %",
    "Average Trend Confidence %",
}


def analyze_eros_regime_quality(history: pd.DataFrame | None) -> pd.DataFrame:
    """Report descriptive quality dimensions for the latest aggregate regime."""
    if history is None or history.empty:
        return pd.DataFrame()
    if not REQUIRED_COLUMNS.issubset(history.columns):
        return pd.DataFrame()

    frame = history.loc[:, list(REQUIRED_COLUMNS)].copy()
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    for column in REQUIRED_COLUMNS - {"Timestamp", "Regime"}:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(
        subset=[
            "Timestamp",
            "Rising Breadth %",
            "Falling Breadth %",
            "Average Trend Confidence %",
        ]
    ).sort_values("Timestamp")
    if frame.empty:
        return pd.DataFrame()

    latest = frame.iloc[-1]
    current_regime = str(latest["Regime"])
    current = frame[frame["Regime"].astype(str) == current_regime].copy()

    streak = 0
    for regime in reversed(frame["Regime"].astype(str).tolist()):
        if regime != current_regime:
            break
        streak += 1

    rising = float(latest["Rising Breadth %"])
    falling = float(latest["Falling Breadth %"])
    breadth_strength = round(abs(rising - falling), 2)
    confidence = round(float(latest["Average Trend Confidence %"]), 2)

    return pd.DataFrame(
        [
            {
                "Current Regime": current_regime,
                "Regime Streak": streak,
                "Current Regime Snapshots": len(current),
                "Latest Rising Breadth %": round(rising, 2),
                "Latest Falling Breadth %": round(falling, 2),
                "Latest Breadth Strength": breadth_strength,
                "Latest Average Trend Confidence %": confidence,
                "Regime Breadth Range": round(
                    float(current["Rising Breadth %"].max() - current["Rising Breadth %"].min()),
                    2,
                ),
                "Regime Confidence Range": round(
                    float(
                        current["Average Trend Confidence %"].max()
                        - current["Average Trend Confidence %"].min()
                    ),
                    2,
                ),
            }
        ]
    )
