"""EROS regime-signal synchronization analytics helpers."""

from __future__ import annotations

import pandas as pd

from scanner.eros_signal_alignment import analyze_eros_signal_alignment


def analyze_eros_regime_signal_sync(
    history: pd.DataFrame | None,
    regime_history: pd.DataFrame | None,
    current_fusion: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Compare current aggregate regime direction with individual signal direction."""
    if regime_history is None or regime_history.empty:
        return pd.DataFrame()

    required = {"Timestamp", "Regime"}
    if not required.issubset(regime_history.columns):
        return pd.DataFrame()

    regimes = regime_history.copy()
    regimes["Timestamp"] = pd.to_datetime(regimes["Timestamp"], errors="coerce")
    regimes = regimes.dropna(subset=["Timestamp"]).sort_values("Timestamp")
    if regimes.empty:
        return pd.DataFrame()

    latest_regime = str(regimes.iloc[-1]["Regime"])
    regime_direction = (
        "RISING"
        if "RISING" in latest_regime
        else "FALLING" if "FALLING" in latest_regime else "NEUTRAL"
    )

    alignment = analyze_eros_signal_alignment(history, current_fusion)
    if alignment.empty:
        return pd.DataFrame()

    result = alignment[
        [
            "Symbol",
            "Exchange",
            "Timestamp",
            "Fusion Score",
            "Direction",
            "Trend Consensus",
            "Trend Confidence %",
            "Confidence",
            "Alignment %",
            "Alignment",
        ]
    ].copy()

    result["Current Regime"] = latest_regime
    result["Regime Direction"] = regime_direction
    result["Signal Direction"] = result["Direction"].where(
        result["Direction"].isin(["RISING", "FALLING"]),
        "NEUTRAL",
    )

    result["Regime-Signal Sync"] = "NEUTRAL"
    directional = result["Signal Direction"].isin(["RISING", "FALLING"])
    result.loc[directional, "Regime-Signal Sync"] = "MISMATCH"
    result.loc[
        directional & result["Signal Direction"].eq(result["Regime Direction"]),
        "Regime-Signal Sync",
    ] = "ALIGNED"

    if regime_direction == "NEUTRAL":
        result["Regime-Signal Sync"] = "NEUTRAL REGIME"

    return (
        result[
            [
                "Symbol",
                "Exchange",
                "Timestamp",
                "Fusion Score",
                "Current Regime",
                "Regime Direction",
                "Signal Direction",
                "Trend Consensus",
                "Trend Confidence %",
                "Confidence",
                "Alignment %",
                "Alignment",
                "Regime-Signal Sync",
            ]
        ]
        .sort_values(
            ["Regime-Signal Sync", "Trend Confidence %", "Fusion Score"],
            ascending=[True, False, False],
            na_position="last",
        )
        .reset_index(drop=True)
    )
