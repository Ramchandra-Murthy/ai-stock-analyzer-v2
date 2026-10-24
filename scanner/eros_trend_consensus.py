"""EROS trend consensus analytics helpers."""

from __future__ import annotations

import pandas as pd

from scanner.eros_multi_window_trend import analyze_eros_multi_window_trend
from scanner.eros_signal_lifecycle import analyze_eros_signal_lifecycle


def analyze_eros_trend_consensus(
    history: pd.DataFrame | None,
    current_fusion: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Cross-check multi-window direction, acceleration, and lifecycle state."""
    multi_window = analyze_eros_multi_window_trend(history)
    if multi_window.empty:
        return pd.DataFrame()

    lifecycle = analyze_eros_signal_lifecycle(history, current_fusion)
    lifecycle_columns = [
        "Symbol",
        "Exchange",
        "Fusion Change",
        "Fusion Acceleration",
        "Trend",
        "Lifecycle",
    ]
    if lifecycle.empty:
        lifecycle = pd.DataFrame(columns=lifecycle_columns)
    else:
        lifecycle = lifecycle[lifecycle_columns]

    result = multi_window.merge(lifecycle, on=["Symbol", "Exchange"], how="left")
    result["Trend Consensus"] = "MIXED"
    result.loc[
        (result["Window Alignment"] == "RISING") & (result["Fusion Change"] > 0),
        "Trend Consensus",
    ] = "RISING CONFIRMED"
    result.loc[
        (result["Window Alignment"] == "FALLING") & (result["Fusion Change"] < 0),
        "Trend Consensus",
    ] = "FALLING CONFIRMED"
    result.loc[
        result["Window Alignment"] == "INSUFFICIENT DATA",
        "Trend Consensus",
    ] = "INSUFFICIENT DATA"

    return (
        result[
            [
                "Symbol",
                "Exchange",
                "Timestamp",
                "Fusion Score",
                "2-observation Change",
                "3-observation Change",
                "5-observation Change",
                "Window Alignment",
                "Fusion Change",
                "Fusion Acceleration",
                "Trend",
                "Lifecycle",
                "Trend Consensus",
            ]
        ]
        .sort_values(
            ["Trend Consensus", "Fusion Score"],
            ascending=[True, False],
        )
        .reset_index(drop=True)
    )
