"""EROS aggregate regime consistency analytics helpers for dashboard reporting."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {
    "Timestamp",
    "Regime",
    "Rising Breadth %",
    "Falling Breadth %",
}


def _breadth_regime(rising: float, falling: float) -> str:
    """Derive the regime implied by directional breadth using EROS thresholds."""
    if rising >= 60:
        return "RISING DOMINANT"
    if falling >= 60:
        return "FALLING DOMINANT"
    return "BALANCED"


def analyze_eros_regime_consistency(history: pd.DataFrame | None) -> pd.DataFrame:
    """Compare recorded EROS regimes with regimes implied by recorded breadth."""
    if history is None or history.empty:
        return pd.DataFrame()
    if not REQUIRED_COLUMNS.issubset(history.columns):
        return pd.DataFrame()

    frame = history.loc[:, list(REQUIRED_COLUMNS)].copy()
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    frame["Rising Breadth %"] = pd.to_numeric(frame["Rising Breadth %"], errors="coerce")
    frame["Falling Breadth %"] = pd.to_numeric(frame["Falling Breadth %"], errors="coerce")
    frame = frame.dropna(subset=["Timestamp", "Rising Breadth %", "Falling Breadth %"]).sort_values(
        "Timestamp"
    )
    frame = frame.drop_duplicates(subset=["Timestamp"], keep="last")
    if frame.empty:
        return pd.DataFrame()

    frame["Regime"] = frame["Regime"].astype(str)
    frame["Breadth-Implied Regime"] = [
        _breadth_regime(rising, falling)
        for rising, falling in zip(
            frame["Rising Breadth %"], frame["Falling Breadth %"], strict=True
        )
    ]
    frame["Consistent"] = frame["Regime"].eq(frame["Breadth-Implied Regime"])

    grouped = frame.groupby("Regime", sort=False)
    result = grouped.agg(
        Snapshots=("Timestamp", "size"),
        Consistent_Snapshots=("Consistent", "sum"),
    ).reset_index()
    result["Consistency %"] = (
        result["Consistent_Snapshots"].div(result["Snapshots"]).mul(100).round(2)
    )

    overall = round(float(frame["Consistent"].mean() * 100), 2)
    result["Overall Consistency %"] = overall

    return result[
        [
            "Regime",
            "Snapshots",
            "Consistent_Snapshots",
            "Consistency %",
            "Overall Consistency %",
        ]
    ]
