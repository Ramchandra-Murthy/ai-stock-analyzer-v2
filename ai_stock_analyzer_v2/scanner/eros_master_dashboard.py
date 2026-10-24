"""EROS master dashboard aggregation helpers."""

from __future__ import annotations

import pandas as pd

from scanner.eros_regime_breadth import analyze_eros_regime_breadth
from scanner.eros_regime_consistency import analyze_eros_regime_consistency
from scanner.eros_regime_duration import analyze_eros_regime_duration
from scanner.eros_regime_momentum import analyze_eros_regime_momentum
from scanner.eros_regime_persistence import analyze_eros_regime_persistence
from scanner.eros_regime_quality import analyze_eros_regime_quality
from scanner.eros_regime_signal_sync import analyze_eros_regime_signal_sync
from scanner.eros_regime_stability import analyze_eros_regime_stability
from scanner.eros_regime_transitions import analyze_eros_regime_transitions
from scanner.eros_signal_alignment import analyze_eros_signal_alignment
from scanner.eros_signal_lifecycle import analyze_eros_signal_lifecycle
from scanner.eros_trend_confidence import analyze_eros_trend_confidence


def build_eros_master_dashboard(
    history: pd.DataFrame | None,
    current_fusion: pd.DataFrame | None = None,
    regime_history: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate existing EROS analytics into a compact summary and signal board."""
    if history is None or history.empty:
        return pd.DataFrame(), pd.DataFrame()

    lifecycle = analyze_eros_signal_lifecycle(history, current_fusion)
    confidence = analyze_eros_trend_confidence(history, current_fusion)
    alignment = analyze_eros_signal_alignment(history, current_fusion)
    regime_sync = analyze_eros_regime_signal_sync(history, regime_history, current_fusion)
    regime_transitions = analyze_eros_regime_transitions(regime_history)
    regime_duration = analyze_eros_regime_duration(regime_history)
    regime_breadth = analyze_eros_regime_breadth(regime_history)
    regime_consistency = analyze_eros_regime_consistency(regime_history)
    regime_persistence = analyze_eros_regime_persistence(regime_history)
    regime_quality = analyze_eros_regime_quality(regime_history)

    signal = (
        history.sort_values("Timestamp").groupby(["Symbol", "Exchange"], as_index=False).tail(1)
    )

    if current_fusion is not None and not current_fusion.empty:
        keys = ["Symbol", "Exchange"]
        if set(keys).issubset(current_fusion.columns):
            signal = current_fusion.copy()

    signal = signal.copy()
    signal_columns = [
        column
        for column in ["Symbol", "Exchange", "Sector", "Fusion Score"]
        if column in signal.columns
    ]
    signal = signal[signal_columns]

    for frame in (lifecycle, confidence, alignment, regime_sync):
        if not frame.empty and {"Symbol", "Exchange"}.issubset(frame.columns):
            columns = [
                column
                for column in frame.columns
                if column
                in {
                    "Symbol",
                    "Exchange",
                    "Lifecycle",
                    "Trend Consensus",
                    "Trend Confidence %",
                    "Confidence",
                    "Trend Quality",
                    "Alignment %",
                    "Alignment",
                    "Persistence",
                    "Current Regime",
                    "Regime Direction",
                    "Signal Direction",
                    "Regime-Signal Sync",
                    "Previous Regime",
                    "Transition",
                    "Direction Transition",
                    "Transition Type",
                }
            ]
            columns = [
                column
                for column in columns
                if column not in {"Symbol", "Exchange"} and column not in signal.columns
            ]
            if columns:
                signal = signal.merge(
                    frame[["Symbol", "Exchange", *columns]],
                    on=["Symbol", "Exchange"],
                    how="left",
                )

    summary_values: dict[str, object] = {
        "Signals": len(signal),
        "Average Fusion Score": (
            round(float(pd.to_numeric(signal["Fusion Score"], errors="coerce").mean()), 2)
            if "Fusion Score" in signal.columns
            else None
        ),
    }

    if "Lifecycle" in signal.columns:
        summary_values["New Signals"] = int((signal["Lifecycle"] == "NEW").sum())
        summary_values["Persistent Signals"] = int((signal["Lifecycle"] == "PERSISTENT").sum())
        summary_values["Accelerating Signals"] = int((signal["Lifecycle"] == "ACCELERATING").sum())
        summary_values["Weakening Signals"] = int((signal["Lifecycle"] == "WEAKENING").sum())
        summary_values["Expired Signals"] = int((signal["Lifecycle"] == "EXPIRED").sum())

    if "Alignment %" in signal.columns:
        alignment_values = pd.to_numeric(signal["Alignment %"], errors="coerce")
        alignment_mean = alignment_values.mean()
        summary_values["Average Signal Alignment %"] = (
            round(float(alignment_mean), 2) if pd.notna(alignment_mean) else None
        )

    if "Regime-Signal Sync" in signal.columns:
        sync = signal["Regime-Signal Sync"]
        summary_values["Regime-Signal Aligned Signals"] = int((sync == "ALIGNED").sum())
        summary_values["Regime-Signal Mismatch Signals"] = int((sync == "MISMATCH").sum())

    if "Trend Confidence %" in signal.columns:
        confidence_values = pd.to_numeric(signal["Trend Confidence %"], errors="coerce")
        confidence_mean = confidence_values.mean()
        summary_values["Average Trend Confidence %"] = (
            round(float(confidence_mean), 2) if pd.notna(confidence_mean) else None
        )

    if regime_history is not None and not regime_history.empty:
        momentum = analyze_eros_regime_momentum(regime_history)
        stability = analyze_eros_regime_stability(regime_history)
        if not momentum.empty:
            row = momentum.iloc[0]
            summary_values["Current Regime"] = row["Current Regime"]
            summary_values["Regime Momentum"] = row["Regime Momentum"]
        if not stability.empty:
            row = stability.iloc[0]
            summary_values["Regime Stability"] = row["Stability"]
            summary_values["Regime Streak"] = row["Regime Streak"]

    if not regime_transitions.empty:
        latest_transition = regime_transitions.iloc[-1]
        summary_values["Regime Transition Count"] = len(regime_transitions)
        summary_values["Latest Regime Transition"] = latest_transition["Transition"]
        summary_values["Latest Transition Timestamp"] = latest_transition["Timestamp"]
        summary_values["Latest Direction Transition"] = latest_transition["Direction Transition"]

    if not regime_duration.empty:
        current_duration = regime_duration.iloc[-1]
        summary_values["Regime Run Count"] = len(regime_duration)
        summary_values["Current Regime Duration Minutes"] = current_duration["Duration Minutes"]
        summary_values["Current Regime Snapshots"] = current_duration["Snapshots"]

    if not regime_breadth.empty:
        current_regime = (
            str(summary_values["Current Regime"])
            if "Current Regime" in summary_values
            else str(regime_breadth.iloc[-1]["Regime"])
        )
        current_breadth = regime_breadth[regime_breadth["Regime"] == current_regime]
        if not current_breadth.empty:
            breadth_row = current_breadth.iloc[-1]
            summary_values["Current Regime Average Rising Breadth %"] = breadth_row[
                "Average_Rising_Breadth"
            ]
            summary_values["Current Regime Average Falling Breadth %"] = breadth_row[
                "Average Falling Breadth"
            ]
            summary_values["Current Regime Average Trend Confidence %"] = breadth_row[
                "Average_Trend_Confidence"
            ]

    if not regime_persistence.empty:
        current_persistence = regime_persistence[regime_persistence["Current Run"]]
        if not current_persistence.empty:
            persistence_row = current_persistence.iloc[0]
            summary_values["Regime Overall Continuation %"] = persistence_row[
                "Overall Continuation %"
            ]
            summary_values["Current Regime Run Snapshots"] = persistence_row[
                "Current Run Snapshots"
            ]
            summary_values["Current Regime Run Duration Minutes"] = persistence_row[
                "Current Run Duration Minutes"
            ]
            summary_values["Current Regime Average Run Snapshots"] = persistence_row[
                "Average_Run_Snapshots"
            ]

    if not regime_consistency.empty:
        summary_values["Regime Overall Consistency %"] = regime_consistency[
            "Overall Consistency %"
        ].iloc[0]

    if not regime_quality.empty:
        quality_row = regime_quality.iloc[0]
        summary_values["Latest Regime Breadth Strength"] = quality_row["Latest Breadth Strength"]
        summary_values["Latest Regime Average Confidence %"] = quality_row[
            "Latest Average Trend Confidence %"
        ]
        summary_values["Current Regime Breadth Range"] = quality_row["Regime Breadth Range"]
        summary_values["Current Regime Confidence Range"] = quality_row["Regime Confidence Range"]

    summary = pd.DataFrame([summary_values])
    return summary, signal.sort_values(
        ["Fusion Score", "Symbol"],
        ascending=[False, True],
        na_position="last",
    ).reset_index(drop=True)
