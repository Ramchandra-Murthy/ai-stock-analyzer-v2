"""Helpers for descriptive intraday risk and trade-planning metrics."""

from __future__ import annotations

import pandas as pd


def risk_plan_frame(
    results: pd.DataFrame,
    risk_budget: float = 1000.0,
    capital_limit: float = 100000.0,
) -> pd.DataFrame:
    """Add position-size and capital-use calculations to existing trade references."""
    if results is None or results.empty:
        return pd.DataFrame(columns=_columns(results))

    frame = results.copy()
    for column in ("Price", "Entry reference", "Stop reference", "Risk per share"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if "Risk per share" not in frame.columns:
        if {"Entry reference", "Stop reference"}.issubset(frame.columns):
            frame["Risk per share"] = (frame["Entry reference"] - frame["Stop reference"]).abs()
        else:
            frame["Risk per share"] = pd.NA

    frame["Risk budget"] = float(max(0.0, risk_budget))
    frame["Capital limit"] = float(max(0.0, capital_limit))
    frame["Risk-based quantity"] = (
        (frame["Risk budget"] / frame["Risk per share"].replace(0, pd.NA)).fillna(0).floordiv(1)
    )
    entry = frame.get("Entry reference", frame.get("Price"))
    frame["Capital-based quantity"] = (
        (float(max(0.0, capital_limit)) / pd.to_numeric(entry, errors="coerce"))
        .fillna(0)
        .floordiv(1)
    )
    frame["Suggested quantity"] = frame[["Risk-based quantity", "Capital-based quantity"]].min(
        axis=1
    )
    frame["Planned capital"] = (
        pd.to_numeric(entry, errors="coerce") * frame["Suggested quantity"]
    ).round(2)
    frame["Planned risk"] = (frame["Risk per share"] * frame["Suggested quantity"]).round(2)

    return frame.reset_index(drop=True)


def _columns(results: pd.DataFrame | None) -> list[str]:
    """Return stable columns for an empty risk-plan frame."""
    base = list(results.columns) if results is not None else []
    return base + [
        column
        for column in (
            "Risk budget",
            "Capital limit",
            "Risk-based quantity",
            "Capital-based quantity",
            "Suggested quantity",
            "Planned capital",
            "Planned risk",
        )
        if column not in base
    ]
