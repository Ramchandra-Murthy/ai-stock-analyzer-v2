"""EROS aggregate regime duration analytics helpers."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {"Timestamp", "Regime"}


def analyze_eros_regime_duration(history: pd.DataFrame | None) -> pd.DataFrame:
    """Measure the duration of each contiguous aggregate EROS regime run."""
    if history is None or history.empty:
        return pd.DataFrame()
    if not REQUIRED_COLUMNS.issubset(history.columns):
        return pd.DataFrame()

    frame = history.loc[:, ["Timestamp", "Regime"]].copy()
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    frame = frame.dropna(subset=["Timestamp"]).sort_values("Timestamp")
    frame["Regime"] = frame["Regime"].astype(str)
    frame = frame.drop_duplicates(subset=["Timestamp"], keep="last")
    if frame.empty:
        return pd.DataFrame()

    run_id = frame["Regime"].ne(frame["Regime"].shift()).cumsum()
    grouped = frame.groupby(run_id, sort=True)
    result = grouped.agg(
        Regime=("Regime", "first"),
        Start=("Timestamp", "min"),
        End=("Timestamp", "max"),
        Snapshots=("Timestamp", "size"),
    ).reset_index(drop=True)

    result["Duration Minutes"] = (
        (result["End"] - result["Start"]).dt.total_seconds().div(60).round(2)
    )
    result["Run Number"] = range(1, len(result) + 1)
    result["Is Current"] = result.index == len(result) - 1

    return result[
        [
            "Run Number",
            "Regime",
            "Start",
            "End",
            "Snapshots",
            "Duration Minutes",
            "Is Current",
        ]
    ]
