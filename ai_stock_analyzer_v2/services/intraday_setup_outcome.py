"""Helpers for tracking observed intraday setup outcomes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from services.intraday_tracking import copy_records, setup_rows


def record_setup_outcomes(
    previous_outcomes: dict[str, dict[str, Any]],
    results: pd.DataFrame,
    observed_at: datetime,
) -> dict[str, dict[str, Any]]:
    """Record price observations relative to the first observed setup."""
    updated = copy_records(previous_outcomes)

    for row in setup_rows(results, ("Symbol", "Plan state", "Price")):
        symbol = str(row[0])
        state = str(row[1])

        try:
            price = float(row[2])
        except (TypeError, ValueError):
            continue

        if price <= 0:
            continue

        previous = updated.get(symbol)
        if previous is None or previous.get("State") != state:
            updated[symbol] = {
                "Symbol": symbol,
                "State": state,
                "First price": price,
                "Current price": price,
                "Price change %": 0.0,
                "First observed": observed_at,
                "Last observed": observed_at,
                "Observations": 1,
            }
            continue

        first_price = float(previous.get("First price", price))
        change = (price / first_price - 1.0) * 100.0 if first_price > 0 else 0.0
        updated[symbol] = {
            **previous,
            "Current price": price,
            "Price change %": round(change, 2),
            "Last observed": observed_at,
            "Observations": int(previous.get("Observations", 0)) + 1,
        }

    return updated


def outcomes_frame(outcomes: dict[str, dict[str, Any]]) -> pd.DataFrame:
    """Build a stable display frame for observed setup outcomes."""
    columns = [
        "Symbol",
        "State",
        "First price",
        "Current price",
        "Price change %",
        "First observed",
        "Last observed",
        "Observations",
    ]
    if not outcomes:
        return pd.DataFrame(columns=columns)

    frame = pd.DataFrame(list(outcomes.values()))
    return (
        frame[columns]
        .sort_values(
            ["Price change %", "Observations", "Symbol"],
            ascending=[False, False, True],
        )
        .reset_index(drop=True)
    )
