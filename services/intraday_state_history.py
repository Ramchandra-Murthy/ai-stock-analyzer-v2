"""Helpers for tracking intraday setup-state transitions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from services.intraday_tracking import setup_rows


def record_setup_state_transitions(
    previous_states: dict[str, str],
    results: pd.DataFrame,
    observed_at: datetime,
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Return updated state memory and transitions seen in the latest scan."""
    updated_states = dict(previous_states)
    transitions: list[dict[str, Any]] = []

    for row in setup_rows(results, ("Symbol", "Plan state")):
        symbol = str(row[0])
        new_state = str(row[1])
        old_state = updated_states.get(symbol)

        if old_state is not None and old_state != new_state:
            transitions.append(
                {
                    "Observed at": observed_at,
                    "Symbol": symbol,
                    "Previous state": old_state,
                    "New state": new_state,
                }
            )

        updated_states[symbol] = new_state

    return updated_states, transitions


def transitions_frame(transitions: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert state-transition records to a displayable DataFrame."""
    columns = ["Observed at", "Symbol", "Previous state", "New state"]
    if not transitions:
        return pd.DataFrame(columns=columns)

    frame = pd.DataFrame(transitions, columns=columns)
    frame["Observed at"] = pd.to_datetime(frame["Observed at"], errors="coerce")
    return frame.sort_values("Observed at", ascending=False).reset_index(drop=True)
