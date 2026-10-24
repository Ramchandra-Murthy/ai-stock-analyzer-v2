"""Helpers for measuring intraday setup outcomes across elapsed time windows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from services.intraday_tracking import copy_records, setup_rows

WINDOWS_MINUTES = (5, 10, 15, 30)


def record_multi_window_outcomes(
    previous: dict[str, dict[str, Any]],
    results: pd.DataFrame,
    observed_at: datetime,
) -> dict[str, dict[str, Any]]:
    """Record setup-state baselines and fill elapsed outcome windows."""
    updated = copy_records(previous)

    for row in setup_rows(results, ("Symbol", "Plan state", "Price")):
        symbol = str(row[0])
        state = str(row[1])
        try:
            price = float(row[2])
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue

        current = updated.get(symbol)
        if current is None or current.get("State") != state:
            current = {
                "Symbol": symbol,
                "State": state,
                "Baseline price": price,
                "Baseline time": observed_at,
                "Observations": 1,
            }
            for minutes in WINDOWS_MINUTES:
                current[f"{minutes}m change %"] = None
            updated[symbol] = current
            continue

        baseline_price = float(current.get("Baseline price", price))
        baseline_time = current.get("Baseline time", observed_at)
        elapsed = (pd.Timestamp(observed_at) - pd.Timestamp(baseline_time)).total_seconds() / 60
        updated_record = {**current, "Observations": int(current.get("Observations", 0)) + 1}

        if baseline_price > 0:
            change = (price / baseline_price - 1.0) * 100.0
            for minutes in WINDOWS_MINUTES:
                key = f"{minutes}m change %"
                if elapsed >= minutes and updated_record.get(key) is None:
                    updated_record[key] = round(change, 2)

        updated[symbol] = updated_record

    return updated


def multi_window_frame(
    outcomes: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Build a stable display frame for elapsed outcome windows."""
    columns = [
        "Symbol",
        "State",
        "Baseline price",
        "5m change %",
        "10m change %",
        "15m change %",
        "30m change %",
        "Observations",
    ]
    if not outcomes:
        return pd.DataFrame(columns=columns)

    frame = pd.DataFrame(list(outcomes.values()))
    frame = frame.rename(
        columns={
            "5m change %": "5m change %",
            "10m change %": "10m change %",
            "15m change %": "15m change %",
            "30m change %": "30m change %",
        }
    )
    return (
        frame[columns]
        .sort_values(
            ["30m change %", "15m change %", "10m change %", "5m change %", "Symbol"],
            ascending=[False, False, False, False, True],
            na_position="last",
        )
        .reset_index(drop=True)
    )
