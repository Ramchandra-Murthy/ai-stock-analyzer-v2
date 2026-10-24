"""EROS aggregate regime persistence analytics helpers."""

from __future__ import annotations

import pandas as pd

from scanner.eros_regime_duration import analyze_eros_regime_duration


def analyze_eros_regime_persistence(history: pd.DataFrame | None) -> pd.DataFrame:
    """Summarize how consistently each aggregate EROS regime persists."""
    runs = analyze_eros_regime_duration(history)
    if runs.empty:
        return pd.DataFrame()

    grouped = runs.groupby("Regime", sort=False)
    result = grouped.agg(
        Runs=("Regime", "size"),
        Total_Snapshots=("Snapshots", "sum"),
        Average_Run_Snapshots=("Snapshots", "mean"),
        Median_Run_Snapshots=("Snapshots", "median"),
        Maximum_Run_Snapshots=("Snapshots", "max"),
        Average_Duration_Minutes=("Duration Minutes", "mean"),
        Median_Duration_Minutes=("Duration Minutes", "median"),
        Maximum_Duration_Minutes=("Duration Minutes", "max"),
    ).reset_index()

    current = runs.loc[runs["Is Current"]].iloc[0]
    result["Current Run Snapshots"] = (
        result["Regime"].map({current["Regime"]: int(current["Snapshots"])}).fillna(0)
    )
    result["Current Run Duration Minutes"] = (
        result["Regime"].map({current["Regime"]: float(current["Duration Minutes"])}).fillna(0.0)
    )
    result["Current Run"] = result["Regime"] == current["Regime"]

    total_links = max(int(runs["Snapshots"].sum()) - 1, 0)
    same_regime_links = max(int(runs["Snapshots"].sub(1).sum()), 0)
    overall_continuation = (
        round(float(same_regime_links / total_links * 100), 2) if total_links else 0.0
    )
    result["Overall Continuation %"] = overall_continuation

    numeric_columns = [
        "Average_Run_Snapshots",
        "Median_Run_Snapshots",
        "Maximum_Run_Snapshots",
        "Average_Duration_Minutes",
        "Median_Duration_Minutes",
        "Maximum_Duration_Minutes",
        "Current Run Duration Minutes",
        "Overall Continuation %",
    ]
    result[numeric_columns] = result[numeric_columns].round(2)

    return result[
        [
            "Regime",
            "Runs",
            "Total_Snapshots",
            "Average_Run_Snapshots",
            "Median_Run_Snapshots",
            "Maximum_Run_Snapshots",
            "Average_Duration_Minutes",
            "Median_Duration_Minutes",
            "Maximum_Duration_Minutes",
            "Current Run",
            "Current Run Snapshots",
            "Current Run Duration Minutes",
            "Overall Continuation %",
        ]
    ]
