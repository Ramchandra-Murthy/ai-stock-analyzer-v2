"""EROS trend confidence analytics helpers."""

from __future__ import annotations

import pandas as pd

from scanner.eros_trend_consensus import analyze_eros_trend_consensus
from scanner.eros_trend_persistence import analyze_eros_trend_persistence
from scanner.eros_trend_quality import analyze_eros_trend_quality


def analyze_eros_trend_confidence(
    history: pd.DataFrame | None,
    current_fusion: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Combine independent EROS trend diagnostics into a transparent confidence score."""
    consensus = analyze_eros_trend_consensus(history, current_fusion)
    persistence = analyze_eros_trend_persistence(history)
    quality = analyze_eros_trend_quality(history)

    if consensus.empty:
        return pd.DataFrame()

    result = consensus[
        [
            "Symbol",
            "Exchange",
            "Timestamp",
            "Fusion Score",
            "Trend Consensus",
        ]
    ].copy()

    persistence_columns = [
        "Symbol",
        "Exchange",
        "Direction",
        "Streak",
        "Directional Consistency %",
        "Persistence",
    ]
    quality_columns = [
        "Symbol",
        "Exchange",
        "Trend Efficiency %",
        "Trend Quality",
    ]

    if not persistence.empty:
        result = result.merge(
            persistence[persistence_columns],
            on=["Symbol", "Exchange"],
            how="left",
        )

    if not quality.empty:
        result = result.merge(
            quality[quality_columns],
            on=["Symbol", "Exchange"],
            how="left",
        )

    result["Consensus Points"] = 0.0
    result.loc[
        result["Trend Consensus"].isin(["RISING CONFIRMED", "FALLING CONFIRMED"]),
        "Consensus Points",
    ] = 40.0
    result.loc[
        result["Trend Consensus"] == "INSUFFICIENT DATA",
        "Consensus Points",
    ] = 0.0

    result["Persistence Points"] = (
        pd.to_numeric(result["Directional Consistency %"], errors="coerce").fillna(0.0) * 0.3
    )
    result["Quality Points"] = (
        pd.to_numeric(result["Trend Efficiency %"], errors="coerce").fillna(0.0) * 0.3
    )
    result["Trend Confidence %"] = (
        result["Consensus Points"] + result["Persistence Points"] + result["Quality Points"]
    ).round(2)

    result["Confidence"] = "LOW"
    result.loc[result["Trend Confidence %"] >= 60, "Confidence"] = "MODERATE"
    result.loc[result["Trend Confidence %"] >= 80, "Confidence"] = "HIGH"
    result.loc[
        result["Trend Consensus"] == "INSUFFICIENT DATA",
        ["Trend Confidence %", "Confidence"],
    ] = [0.0, "INSUFFICIENT DATA"]

    return (
        result[
            [
                "Symbol",
                "Exchange",
                "Timestamp",
                "Fusion Score",
                "Trend Consensus",
                "Direction",
                "Streak",
                "Directional Consistency %",
                "Persistence",
                "Trend Efficiency %",
                "Trend Quality",
                "Trend Confidence %",
                "Confidence",
            ]
        ]
        .sort_values(
            ["Trend Confidence %", "Fusion Score"],
            ascending=[False, False],
        )
        .reset_index(drop=True)
    )
