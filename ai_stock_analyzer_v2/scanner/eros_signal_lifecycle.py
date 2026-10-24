"""EROS signal lifecycle analytics helpers."""

from __future__ import annotations  # noqa: I001

import pandas as pd

from scanner.eros_fusion_history_analytics import prepare_eros_fusion_history
from scanner.eros_fusion_trend import analyze_eros_fusion_trend

LIFECYCLE_STATES = (
    "NEW",
    "CONFIRMED",
    "PERSISTENT",
    "ACCELERATING",
    "WEAKENING",
    "EXPIRED",
)


def analyze_eros_signal_lifecycle(
    history: pd.DataFrame | None,
    current_fusion: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Classify the current lifecycle state of each EROS fusion signal."""
    frame = prepare_eros_fusion_history(history)
    if frame.empty:
        return pd.DataFrame()

    latest = (
        frame.sort_values(["Symbol", "Exchange", "Timestamp"])
        .groupby(["Symbol", "Exchange"], as_index=False)
        .tail(1)
        .copy()
    )
    counts = (
        frame.groupby(["Symbol", "Exchange"], as_index=False)
        .size()
        .rename(columns={"size": "Observations"})
    )
    trend = analyze_eros_fusion_trend(frame)
    result = latest.merge(counts, on=["Symbol", "Exchange"], how="left")
    result = result.merge(
        trend[
            [
                "Symbol",
                "Exchange",
                "Fusion Change",
                "Fusion Acceleration",
                "Trend",
            ]
        ],
        on=["Symbol", "Exchange"],
        how="left",
    )

    if current_fusion is None or current_fusion.empty:
        current_keys: set[tuple[object, object]] = set()
    elif {"Symbol", "Exchange"}.issubset(current_fusion.columns):
        current_keys = set(zip(current_fusion["Symbol"], current_fusion["Exchange"], strict=True))
    else:
        current_keys = set()

    result["Lifecycle"] = "CONFIRMED"
    result.loc[result["Observations"] <= 1, "Lifecycle"] = "NEW"
    result.loc[
        (result["Observations"] >= 3) & (result["Fusion Change"] >= 0),
        "Lifecycle",
    ] = "PERSISTENT"
    result.loc[
        (result["Observations"] >= 3)
        & (result["Fusion Change"] > 0)
        & (result["Fusion Acceleration"] > 0),
        "Lifecycle",
    ] = "ACCELERATING"
    result.loc[result["Fusion Change"] < 0, "Lifecycle"] = "WEAKENING"

    if current_keys:
        result.loc[
            ~result.apply(
                lambda row: (row["Symbol"], row["Exchange"]) in current_keys,
                axis=1,
            ),
            "Lifecycle",
        ] = "EXPIRED"

    return (
        result[
            [
                "Symbol",
                "Exchange",
                "Timestamp",
                "Fusion Score",
                "Observations",
                "Fusion Change",
                "Fusion Acceleration",
                "Trend",
                "Lifecycle",
            ]
        ]
        .sort_values(
            ["Lifecycle", "Fusion Score", "Fusion Change"],
            ascending=[True, False, False],
        )
        .reset_index(drop=True)
    )
