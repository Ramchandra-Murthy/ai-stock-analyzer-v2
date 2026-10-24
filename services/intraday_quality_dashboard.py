"""Helpers for a consolidated intraday setup quality summary."""

from __future__ import annotations

from typing import Any

import pandas as pd


def dashboard_summary(
    states: dict[str, str],
    monitor: dict[str, dict[str, Any]],
    outcomes: dict[str, dict[str, Any]],
    transitions: list[dict[str, Any]],
    windows: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Return stable KPI rows for the current intraday session."""
    outcome_values = list(outcomes.values())
    changes = pd.to_numeric(
        pd.Series([item.get("Price change %") for item in outcome_values]),
        errors="coerce",
    ).dropna()
    window_values = list(windows.values())

    rows = [
        ("Active setup states", len(states)),
        ("Persisting setups", len(monitor)),
        ("Observed setup outcomes", len(outcomes)),
        ("State transitions", len(transitions)),
        ("Positive observed outcomes", int((changes > 0).sum())),
        ("Negative observed outcomes", int((changes < 0).sum())),
        ("5m windows filled", _filled_windows(window_values, "5m change %")),
        ("10m windows filled", _filled_windows(window_values, "10m change %")),
        ("15m windows filled", _filled_windows(window_values, "15m change %")),
        ("30m windows filled", _filled_windows(window_values, "30m change %")),
    ]
    return pd.DataFrame(rows, columns=["Metric", "Value"])


def _filled_windows(
    records: list[dict[str, Any]],
    key: str,
) -> int:
    """Count outcome records with a completed time window."""
    return sum(record.get(key) is not None for record in records)
