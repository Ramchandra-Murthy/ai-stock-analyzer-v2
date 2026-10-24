"""EROS signal alignment analytics helpers."""

from __future__ import annotations

import pandas as pd

from scanner.eros_signal_lifecycle import analyze_eros_signal_lifecycle
from scanner.eros_trend_confidence import analyze_eros_trend_confidence


def analyze_eros_signal_alignment(
    history: pd.DataFrame | None,
    current_fusion: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Measure agreement among independent EROS lifecycle and trend diagnostics."""
    confidence = analyze_eros_trend_confidence(history, current_fusion)
    lifecycle = analyze_eros_signal_lifecycle(history, current_fusion)

    if confidence.empty:
        return pd.DataFrame()

    result = confidence[
        [
            "Symbol",
            "Exchange",
            "Timestamp",
            "Fusion Score",
            "Trend Consensus",
            "Direction",
            "Trend Quality",
            "Trend Confidence %",
            "Confidence",
        ]
    ].copy()

    if not lifecycle.empty:
        result = result.merge(
            lifecycle[
                [
                    "Symbol",
                    "Exchange",
                    "Lifecycle",
                    "Fusion Change",
                    "Fusion Acceleration",
                    "Trend",
                ]
            ],
            on=["Symbol", "Exchange"],
            how="left",
        )

    result["Directional Diagnostics"] = 0
    result["Aligned Diagnostics"] = 0

    result.loc[
        result["Direction"].isin(["RISING", "FALLING"]),
        "Directional Diagnostics",
    ] += 1
    result.loc[
        result["Trend"].isin(["RISING", "FALLING"]),
        "Directional Diagnostics",
    ] += 1

    result["Trend Direction"] = result["Trend Consensus"].map(
        {
            "RISING CONFIRMED": "RISING",
            "FALLING CONFIRMED": "FALLING",
        }
    )

    result.loc[
        result["Trend Direction"].notna() & result["Direction"].eq(result["Trend Direction"]),
        "Aligned Diagnostics",
    ] += 1
    result.loc[
        result["Trend Direction"].notna() & result["Trend"].eq(result["Trend Direction"]),
        "Aligned Diagnostics",
    ] += 1
    result.loc[
        result["Direction"].notna() & result["Direction"].eq(result["Trend"]),
        "Aligned Diagnostics",
    ] += 1

    directional = pd.to_numeric(result["Directional Diagnostics"], errors="coerce").astype(
        "Float64"
    )
    aligned = pd.to_numeric(result["Aligned Diagnostics"], errors="coerce").astype("Float64")
    denominator = directional.mask(directional.eq(0))

    result["Alignment %"] = aligned.div(denominator).mul(100).clip(upper=100).round(2)

    result["Alignment"] = "INSUFFICIENT DATA"
    result.loc[result["Directional Diagnostics"] > 0, "Alignment"] = "MIXED"
    result.loc[
        (result["Directional Diagnostics"] >= 2) & (result["Aligned Diagnostics"] >= 2),
        "Alignment",
    ] = "ALIGNED"
    result.loc[
        (result["Directional Diagnostics"] >= 2) & (result["Aligned Diagnostics"] == 1),
        "Alignment",
    ] = "PARTIAL"

    return (
        result[
            [
                "Symbol",
                "Exchange",
                "Timestamp",
                "Fusion Score",
                "Direction",
                "Trend",
                "Trend Consensus",
                "Trend Quality",
                "Lifecycle",
                "Trend Confidence %",
                "Confidence",
                "Directional Diagnostics",
                "Aligned Diagnostics",
                "Alignment %",
                "Alignment",
            ]
        ]
        .sort_values(
            ["Alignment %", "Trend Confidence %", "Fusion Score"],
            ascending=[False, False, False],
            na_position="last",
        )
        .reset_index(drop=True)
    )
