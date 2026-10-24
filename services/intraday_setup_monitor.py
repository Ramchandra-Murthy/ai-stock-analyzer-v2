"""Helpers for monitoring intraday setup persistence between scans."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from services.intraday_tracking import copy_records, setup_rows


def record_setup_observations(
    previous_monitor: dict[str, dict[str, Any]],
    results: pd.DataFrame,
    observed_at: datetime,
) -> dict[str, dict[str, Any]]:
    """Update per-symbol setup observations for the current scan."""
    updated = copy_records(previous_monitor)

    for row in setup_rows(results, ("Symbol", "Plan state")):
        symbol = str(row[0])
        new_state = str(row[1])
        previous = updated.get(symbol)

        if previous is None:
            updated[symbol] = {
                "Symbol": symbol,
                "Current state": new_state,
                "First observed": observed_at,
                "Last observed": observed_at,
                "Observations": 1,
                "State changes": 0,
                "State started": observed_at,
            }
            continue

        state_changes = int(previous.get("State changes", 0))
        state_started = previous.get("State started", observed_at)
        if previous.get("Current state") != new_state:
            state_changes += 1
            state_started = observed_at

        updated[symbol] = {
            **previous,
            "Symbol": symbol,
            "Current state": new_state,
            "First observed": previous.get("First observed", observed_at),
            "Last observed": observed_at,
            "Observations": int(previous.get("Observations", 0)) + 1,
            "State changes": state_changes,
            "State started": state_started,
        }

    return updated


def monitor_frame(
    monitor: dict[str, dict[str, Any]],
    observed_at: datetime | None = None,
) -> pd.DataFrame:
    """Build a display frame showing setup persistence and state changes."""
    columns = [
        "Symbol",
        "Current state",
        "Observations",
        "State changes",
        "First observed",
        "Last observed",
        "Current state duration (min)",
    ]
    if not monitor:
        return pd.DataFrame(columns=columns)

    now = observed_at or datetime.now().astimezone()
    frame = pd.DataFrame(list(monitor.values()))
    frame["Current state duration (min)"] = (
        (pd.to_datetime(now) - pd.to_datetime(frame["State started"]))
        .dt.total_seconds()
        .div(60)
        .clip(lower=0)
        .round(1)
    )
    frame = frame.rename(
        columns={
            "First observed": "First observed",
            "Last observed": "Last observed",
        }
    )
    return (
        frame[columns]
        .sort_values(
            ["State changes", "Observations", "Symbol"],
            ascending=[False, False, True],
        )
        .reset_index(drop=True)
    )
