"""Consolidated descriptive EROS regime dashboard snapshot."""

from __future__ import annotations

import pandas as pd

from scanner.eros_regime_breadth import analyze_eros_regime_breadth
from scanner.eros_regime_consistency import analyze_eros_regime_consistency
from scanner.eros_regime_duration import analyze_eros_regime_duration
from scanner.eros_regime_momentum import analyze_eros_regime_momentum
from scanner.eros_regime_persistence import analyze_eros_regime_persistence
from scanner.eros_regime_quality import analyze_eros_regime_quality
from scanner.eros_regime_stability import analyze_eros_regime_stability
from scanner.eros_regime_transitions import analyze_eros_regime_transitions


def build_eros_regime_dashboard_snapshot(
    regime_history: pd.DataFrame | None,
) -> pd.DataFrame:
    """Combine existing regime analytics into one descriptive current-state row."""
    if regime_history is None or regime_history.empty:
        return pd.DataFrame()

    snapshot: dict[str, object] = {}

    analyzers = (
        analyze_eros_regime_momentum,
        analyze_eros_regime_stability,
        analyze_eros_regime_quality,
    )
    for analyzer in analyzers:
        result = analyzer(regime_history)
        if not result.empty:
            snapshot.update(result.iloc[0].to_dict())

    breadth = analyze_eros_regime_breadth(regime_history)
    if not breadth.empty:
        current_regime = str(snapshot.get("Current Regime", breadth.iloc[-1]["Regime"]))
        current = breadth[breadth["Regime"].astype(str) == current_regime]
        if not current.empty:
            snapshot.update(
                {
                    "Average Rising Breadth %": current.iloc[-1]["Average_Rising_Breadth"],
                    "Average Falling Breadth %": current.iloc[-1]["Average Falling Breadth"],
                    "Average Trend Confidence %": current.iloc[-1]["Average_Trend_Confidence"],
                }
            )

    duration = analyze_eros_regime_duration(regime_history)
    if not duration.empty:
        current = duration.iloc[-1]
        snapshot.update(
            {
                "Current Duration Minutes": current["Duration Minutes"],
                "Current Duration Snapshots": current["Snapshots"],
            }
        )

    persistence = analyze_eros_regime_persistence(regime_history)
    if not persistence.empty:
        current = persistence[persistence["Current Run"]]
        if not current.empty:
            row = current.iloc[0]
            snapshot.update(
                {
                    "Continuation %": row["Overall Continuation %"],
                    "Current Run Snapshots": row["Current Run Snapshots"],
                }
            )

    consistency = analyze_eros_regime_consistency(regime_history)
    if not consistency.empty:
        snapshot["Consistency %"] = consistency.iloc[0]["Overall Consistency %"]

    transitions = analyze_eros_regime_transitions(regime_history)
    if not transitions.empty:
        latest = transitions.iloc[-1]
        snapshot.update(
            {
                "Transition Count": len(transitions),
                "Latest Transition": latest["Transition"],
                "Latest Transition Timestamp": latest["Timestamp"],
            }
        )

    return pd.DataFrame([snapshot]) if snapshot else pd.DataFrame()
