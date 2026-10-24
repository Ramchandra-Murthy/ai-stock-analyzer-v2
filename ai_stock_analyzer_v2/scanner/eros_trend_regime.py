"""EROS trend breadth and regime analytics helpers."""

from __future__ import annotations

import pandas as pd


def analyze_eros_trend_regime(confidence: pd.DataFrame | None) -> pd.DataFrame:
    """Summarize the latest EROS trend distribution across the scanned universe."""
    if confidence is None or confidence.empty:
        return pd.DataFrame()

    required = {"Trend Consensus", "Confidence", "Trend Confidence %"}
    if not required.issubset(confidence.columns):
        return pd.DataFrame()

    frame = confidence.copy()
    total = len(frame)
    if total == 0:
        return pd.DataFrame()

    consensus = frame["Trend Consensus"].astype(str)
    confidence_band = frame["Confidence"].astype(str)

    rising = int((consensus == "RISING CONFIRMED").sum())
    falling = int((consensus == "FALLING CONFIRMED").sum())
    mixed = int((consensus == "MIXED").sum())
    insufficient = int((consensus == "INSUFFICIENT DATA").sum())

    high = int((confidence_band == "HIGH").sum())
    moderate = int((confidence_band == "MODERATE").sum())
    low = int((confidence_band == "LOW").sum())

    directional = rising + falling
    rising_breadth = round(100.0 * rising / directional, 2) if directional else 0.0
    falling_breadth = round(100.0 * falling / directional, 2) if directional else 0.0

    if directional == 0:
        regime = "INSUFFICIENT DATA"
    elif rising_breadth >= 60:
        regime = "RISING DOMINANT"
    elif falling_breadth >= 60:
        regime = "FALLING DOMINANT"
    else:
        regime = "BALANCED"

    scores = pd.to_numeric(frame["Trend Confidence %"], errors="coerce").dropna()
    average_confidence = round(float(scores.mean()), 2) if not scores.empty else 0.0

    return pd.DataFrame(
        [
            {
                "Signals": total,
                "Rising Confirmed": rising,
                "Falling Confirmed": falling,
                "Mixed": mixed,
                "Insufficient Data": insufficient,
                "High Confidence": high,
                "Moderate Confidence": moderate,
                "Low Confidence": low,
                "Rising Breadth %": rising_breadth,
                "Falling Breadth %": falling_breadth,
                "Average Trend Confidence %": average_confidence,
                "Regime": regime,
            }
        ]
    )
