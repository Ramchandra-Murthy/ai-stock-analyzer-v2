"""EROS trend transition analytics helpers."""

from __future__ import annotations

import pandas as pd

from scanner.eros_fusion_history_analytics import prepare_eros_fusion_history


def analyze_eros_trend_transitions(history: pd.DataFrame | None) -> pd.DataFrame:
    """Detect the latest directional transition in each EROS fusion history."""
    frame = prepare_eros_fusion_history(history)
    if frame.empty:
        return pd.DataFrame()

    frame = frame.sort_values(["Symbol", "Exchange", "Timestamp"]).copy()
    frame["Fusion Change"] = frame.groupby(["Symbol", "Exchange"])["Fusion Score"].diff()
    frame["Previous Change"] = frame.groupby(["Symbol", "Exchange"])["Fusion Change"].shift(1)

    latest = frame.groupby(["Symbol", "Exchange"], as_index=False).tail(1).copy()
    latest["Observations"] = (
        frame.groupby(["Symbol", "Exchange"])["Fusion Score"].transform("size").loc[latest.index]
    )

    def classify(row: pd.Series) -> str:
        change = row["Fusion Change"]
        previous = row["Previous Change"]
        if pd.isna(change):
            return "NEW"
        if change == 0:
            return "STABLE"
        if pd.isna(previous) or previous == 0:
            return "INITIAL RISE" if change > 0 else "INITIAL FALL"
        if change > 0 and previous < 0:
            return "REVERSAL TO RISING"
        if change < 0 and previous > 0:
            return "REVERSAL TO FALLING"
        if change > 0:
            return "CONTINUING RISING"
        return "CONTINUING FALLING"

    latest["Trend Transition"] = latest.apply(classify, axis=1)
    latest["Previous Change"] = latest["Previous Change"].fillna(0.0)
    latest["Fusion Change"] = latest["Fusion Change"].fillna(0.0)

    return (
        latest[
            [
                "Symbol",
                "Exchange",
                "Timestamp",
                "Fusion Score",
                "Observations",
                "Previous Change",
                "Fusion Change",
                "Trend Transition",
            ]
        ]
        .sort_values(
            ["Trend Transition", "Fusion Change", "Fusion Score"],
            ascending=[True, False, False],
        )
        .reset_index(drop=True)
    )
