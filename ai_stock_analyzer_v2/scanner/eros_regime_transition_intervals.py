"""Descriptive timing analytics for EROS regime transitions."""

from __future__ import annotations

import pandas as pd

from scanner.eros_regime_transitions import analyze_eros_regime_transitions


def analyze_eros_regime_transition_intervals(
    history: pd.DataFrame | None,
) -> pd.DataFrame:
    """Describe elapsed time between consecutive EROS regime transitions."""
    transitions = analyze_eros_regime_transitions(history)
    if transitions.empty:
        return pd.DataFrame()

    transitions = transitions[
        ["Timestamp", "Previous Regime", "Regime", "Transition", "Transition Count"]
    ].copy()
    transitions["Previous Transition Timestamp"] = transitions["Timestamp"].shift(1)
    transitions["Minutes Since Previous Transition"] = (
        (transitions["Timestamp"] - transitions["Previous Transition Timestamp"])
        .dt.total_seconds()
        .div(60)
        .round(2)
    )

    transitions = transitions.rename(columns={"Regime": "Current Regime"})
    return transitions[
        [
            "Timestamp",
            "Previous Regime",
            "Current Regime",
            "Transition",
            "Previous Transition Timestamp",
            "Minutes Since Previous Transition",
            "Transition Count",
        ]
    ].reset_index(drop=True)
