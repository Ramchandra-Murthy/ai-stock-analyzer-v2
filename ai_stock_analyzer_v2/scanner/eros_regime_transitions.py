"""EROS aggregate regime transition analytics helpers."""

from __future__ import annotations

import pandas as pd

REGIME_DIRECTIONS = {
    "RISING DOMINANT": "RISING",
    "FALLING DOMINANT": "FALLING",
    "BALANCED": "NEUTRAL",
    "INSUFFICIENT DATA": "NEUTRAL",
}

REQUIRED_COLUMNS = {"Timestamp", "Regime"}


def _direction(regime: object) -> str:
    """Map an aggregate regime label to a directional category."""
    label = str(regime)
    if label in REGIME_DIRECTIONS:
        return REGIME_DIRECTIONS[label]
    if "RISING" in label:
        return "RISING"
    if "FALLING" in label:
        return "FALLING"
    return "NEUTRAL"


def _transition_type(previous: str, current: str) -> str:
    """Classify a directional regime transition."""
    if previous == current:
        return "DIRECTION UNCHANGED"
    if previous == "NEUTRAL":
        return "FROM NEUTRAL"
    if current == "NEUTRAL":
        return "TO NEUTRAL"
    return "DIRECTION REVERSAL"


def analyze_eros_regime_transitions(history: pd.DataFrame | None) -> pd.DataFrame:
    """Return every aggregate EROS regime change in chronological order."""
    if history is None or history.empty:
        return pd.DataFrame()
    if not REQUIRED_COLUMNS.issubset(history.columns):
        return pd.DataFrame()

    frame = history.loc[:, ["Timestamp", "Regime"]].copy()
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    frame = frame.dropna(subset=["Timestamp"]).sort_values("Timestamp")
    frame = frame.drop_duplicates(subset=["Timestamp"], keep="last")
    if len(frame) < 2:
        return pd.DataFrame()

    frame["Regime"] = frame["Regime"].astype(str)
    frame["Direction"] = frame["Regime"].map(_direction)

    previous_regime = frame["Regime"].shift(1)
    previous_direction = frame["Direction"].shift(1)
    changed = previous_regime.notna() & frame["Regime"].ne(previous_regime)

    transitions = frame.loc[changed].copy()
    if transitions.empty:
        return pd.DataFrame()

    transitions["Previous Regime"] = previous_regime.loc[changed].to_numpy()
    transitions["Previous Direction"] = previous_direction.loc[changed].to_numpy()
    transitions["Current Direction"] = transitions["Direction"]
    transitions["Transition"] = transitions["Previous Regime"] + " → " + transitions["Regime"]
    transitions["Direction Transition"] = (
        transitions["Previous Direction"] + " → " + transitions["Current Direction"]
    )
    transitions["Transition Type"] = [
        _transition_type(previous, current)
        for previous, current in zip(
            transitions["Previous Direction"],
            transitions["Current Direction"],
            strict=True,
        )
    ]
    transitions["Transition Count"] = range(1, len(transitions) + 1)

    return transitions[
        [
            "Timestamp",
            "Previous Regime",
            "Regime",
            "Previous Direction",
            "Current Direction",
            "Transition",
            "Direction Transition",
            "Transition Type",
            "Transition Count",
        ]
    ].reset_index(drop=True)
