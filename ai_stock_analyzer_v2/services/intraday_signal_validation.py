"""Helpers for a consolidated intraday signal validation view."""

from __future__ import annotations

from typing import Any

import pandas as pd

VALIDATION_COLUMNS = [
    "Symbol",
    "Exchange",
    "State",
    "Direction",
    "Setup",
    "First observed",
    "Last observed",
    "Observations",
    "Current price",
    "Price change %",
    "5m change %",
    "10m change %",
    "15m change %",
    "30m change %",
    "Outcome",
]


def build_signal_validation_frame(
    outcomes: dict[str, dict[str, Any]],
    windows: dict[str, dict[str, Any]],
    results: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Combine observed setup outcomes with elapsed validation windows."""
    if not outcomes:
        return pd.DataFrame(columns=VALIDATION_COLUMNS)

    frame = pd.DataFrame(list(outcomes.values()))
    required = {
        "Symbol",
        "State",
        "First observed",
        "Last observed",
        "Observations",
        "Current price",
        "Price change %",
    }
    if not required.issubset(frame.columns):
        return pd.DataFrame(columns=VALIDATION_COLUMNS)

    window_frame = pd.DataFrame(list(windows.values())) if windows else pd.DataFrame()
    if not window_frame.empty and {"Symbol", "State"}.issubset(window_frame.columns):
        window_columns = [
            column
            for column in [
                "Symbol",
                "State",
                "5m change %",
                "10m change %",
                "15m change %",
                "30m change %",
            ]
            if column in window_frame.columns
        ]
        frame = frame.merge(
            window_frame[window_columns],
            on=["Symbol", "State"],
            how="left",
            suffixes=("", "_window"),
        )

    if results is not None and not results.empty and "Symbol" in results.columns:
        context_columns = [
            column
            for column in ["Symbol", "Exchange", "Direction", "Day-trading setup"]
            if column in results.columns
        ]
        if context_columns:
            context = results[context_columns].drop_duplicates("Symbol")
            frame = frame.merge(
                context,
                on="Symbol",
                how="left",
                suffixes=("", "_current"),
            )

    frame["Outcome"] = frame["Price change %"].apply(_outcome_label)

    for column in [
        "Price change %",
        "5m change %",
        "10m change %",
        "15m change %",
        "30m change %",
    ]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").round(2)

    for column in VALIDATION_COLUMNS:
        if column not in frame.columns:
            frame[column] = None

    return (
        frame[VALIDATION_COLUMNS]
        .sort_values(
            ["Outcome", "Price change %", "Observations", "Symbol"],
            ascending=[True, False, False, True],
            na_position="last",
        )
        .reset_index(drop=True)
    )


def validation_summary(validation: pd.DataFrame) -> pd.DataFrame:
    """Return compact counts for observed validation outcomes."""
    rows = []
    if validation.empty or "Outcome" not in validation.columns:
        values = {"Positive": 0, "Negative": 0, "Flat": 0, "Unresolved": 0}
    else:
        counts = validation["Outcome"].value_counts()
        values = {
            label: int(counts.get(label, 0))
            for label in ("Positive", "Negative", "Flat", "Unresolved")
        }

    rows.extend((label, value) for label, value in values.items())
    rows.append(("Tracked setups", len(validation)))
    return pd.DataFrame(rows, columns=["Metric", "Value"])


def _outcome_label(change: object) -> str:
    value = pd.to_numeric(pd.Series([change]), errors="coerce").iloc[0]
    if pd.isna(value):
        return "Unresolved"
    if value > 0:
        return "Positive"
    if value < 0:
        return "Negative"
    return "Flat"
