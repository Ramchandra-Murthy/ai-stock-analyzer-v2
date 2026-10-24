"""EROS regime stability analytics helpers."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {
    "Timestamp",
    "Regime",
    "Rising Breadth %",
    "Average Trend Confidence %",
}


def analyze_eros_regime_stability(history: pd.DataFrame | None) -> pd.DataFrame:
    """Measure persistence and variability of the latest aggregate regime."""
    if history is None or history.empty:
        return pd.DataFrame()
    if not REQUIRED_COLUMNS.issubset(history.columns):
        return pd.DataFrame()

    frame = history.loc[
        :,
        [
            "Timestamp",
            "Regime",
            "Rising Breadth %",
            "Average Trend Confidence %",
        ],
    ].copy()
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    frame = frame.dropna(subset=["Timestamp"]).sort_values("Timestamp")
    if frame.empty:
        return pd.DataFrame()

    latest = frame.iloc[-1]
    latest_regime = str(latest["Regime"])
    regimes = frame["Regime"].astype(str).tolist()

    streak = 0
    for regime in reversed(regimes):
        if regime != latest_regime:
            break
        streak += 1

    current = frame[frame["Regime"].astype(str) == latest_regime]
    breadth_range = round(
        float(current["Rising Breadth %"].max() - current["Rising Breadth %"].min()),
        2,
    )
    confidence_range = round(
        float(
            current["Average Trend Confidence %"].max()
            - current["Average Trend Confidence %"].min()
        ),
        2,
    )

    if streak >= 5 and breadth_range <= 10 and confidence_range <= 10:
        stability = "HIGH"
    elif streak >= 3 and breadth_range <= 20 and confidence_range <= 20:
        stability = "MODERATE"
    elif streak >= 2:
        stability = "LOW"
    else:
        stability = "INITIAL"

    return pd.DataFrame(
        [
            {
                "Current Regime": latest_regime,
                "Regime Streak": streak,
                "Stability": stability,
                "Regime Snapshots": len(current),
                "Rising Breadth Range": breadth_range,
                "Confidence Range": confidence_range,
                "Latest Rising Breadth %": float(latest["Rising Breadth %"]),
                "Latest Falling Breadth %": float(100.0 - float(latest["Rising Breadth %"])),
                "Latest Average Confidence %": float(latest["Average Trend Confidence %"]),
                "Total Snapshots": len(frame),
            }
        ]
    )
