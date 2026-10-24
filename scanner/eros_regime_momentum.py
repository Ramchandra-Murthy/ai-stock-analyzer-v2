"""EROS regime momentum analytics helpers."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {
    "Timestamp",
    "Rising Breadth %",
    "Falling Breadth %",
    "Average Trend Confidence %",
    "Regime",
}


def analyze_eros_regime_momentum(history: pd.DataFrame | None) -> pd.DataFrame:
    """Measure recent aggregate regime momentum from session history."""
    if history is None or history.empty:
        return pd.DataFrame()

    if not REQUIRED_COLUMNS.issubset(history.columns):
        return pd.DataFrame()

    frame = history.copy()
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    for column in (
        "Rising Breadth %",
        "Falling Breadth %",
        "Average Trend Confidence %",
    ):
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
    previous = frame.iloc[-2] if len(frame) >= 2 else None

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
    confidence_delta = (
        round(
            float(latest["Average Trend Confidence %"])
            - float(previous["Average Trend Confidence %"]),
            2,
        )
        if previous is not None
        else None
    )

    if previous is None:
        momentum = "INITIAL"
    elif rising_delta is None or confidence_delta is None:
        momentum = "INSUFFICIENT DATA"
    elif rising_delta >= 5 and confidence_delta >= 3:
        momentum = "RISING STRENGTH"
    elif rising_delta <= -5 and confidence_delta <= -3:
        momentum = "RISING WEAKNESS"
    elif rising_delta <= -5 and confidence_delta >= 3:
        momentum = "FALLING STRENGTH"
    elif rising_delta >= 5 and confidence_delta <= -3:
        momentum = "FALLING WEAKNESS"
    elif abs(rising_delta) < 5 and abs(confidence_delta) < 3:
        momentum = "STABLE"
    else:
        momentum = "MIXED"

    return pd.DataFrame(
        [
            {
                "Latest Timestamp": latest["Timestamp"],
                "Current Regime": str(latest["Regime"]),
                "Rising Breadth Δ": rising_delta,
                "Falling Breadth Δ": falling_delta,
                "Confidence Δ": confidence_delta,
                "Current Rising Breadth %": float(latest["Rising Breadth %"]),
                "Current Falling Breadth %": float(latest["Falling Breadth %"]),
                "Current Average Confidence %": float(latest["Average Trend Confidence %"]),
                "Regime Momentum": momentum,
                "Snapshots": len(frame),
            }
        ]
    )
