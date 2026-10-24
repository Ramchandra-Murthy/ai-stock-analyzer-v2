"""EROS fusion trend and acceleration analytics."""

from __future__ import annotations

import pandas as pd

from scanner.eros_fusion_history_analytics import prepare_eros_fusion_history


def analyze_eros_fusion_trend(
    history: pd.DataFrame | None,
) -> pd.DataFrame:
    """Calculate latest fusion change, acceleration, and direction per symbol."""
    frame = prepare_eros_fusion_history(history)
    if frame.empty:
        return pd.DataFrame()

    frame = frame.sort_values(["Symbol", "Exchange", "Timestamp"]).reset_index(drop=True)
    frame["Fusion Change"] = frame.groupby(["Symbol", "Exchange"])["Fusion Score"].diff()
    frame["Previous Change"] = frame.groupby(["Symbol", "Exchange"])["Fusion Change"].shift(1)
    frame["Fusion Acceleration"] = frame["Fusion Change"] - frame["Previous Change"].fillna(0.0)

    latest = frame.groupby(["Symbol", "Exchange"], as_index=False).tail(1).copy()
    latest["Fusion Change"] = latest["Fusion Change"].fillna(0.0)
    latest["Fusion Acceleration"] = latest["Fusion Acceleration"].fillna(0.0)
    latest["Trend"] = "STABLE"
    latest.loc[latest["Fusion Change"] > 0, "Trend"] = "RISING"
    latest.loc[latest["Fusion Change"] < 0, "Trend"] = "FALLING"
    latest = latest.drop(columns=["Previous Change"], errors="ignore")
    return (
        latest[
            [
                "Symbol",
                "Exchange",
                "Timestamp",
                "Fusion Score",
                "Fusion Change",
                "Fusion Acceleration",
                "Trend",
            ]
        ]
        .sort_values(
            ["Fusion Change", "Fusion Acceleration", "Fusion Score"],
            ascending=[False, False, False],
        )
        .reset_index(drop=True)
    )
