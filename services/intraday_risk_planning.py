"""Helpers for descriptive intraday risk and trade-planning metrics."""

from __future__ import annotations

import math

import pandas as pd


def risk_plan_frame(
    results: pd.DataFrame,
    risk_budget: float = 1000.0,
    capital_limit: float = 100000.0,
) -> pd.DataFrame:
    """Add whole-share position sizes, failing closed for invalid row data."""
    if results is None or results.empty:
        return pd.DataFrame(columns=_columns(results))

    try:
        risk_budget = float(risk_budget)
        capital_limit = float(capital_limit)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("risk_budget and capital_limit must be finite numbers") from exc
    if not math.isfinite(risk_budget) or risk_budget < 0:
        raise ValueError("risk_budget must be finite and non-negative")
    if not math.isfinite(capital_limit) or capital_limit < 0:
        raise ValueError("capital_limit must be finite and non-negative")

    frame = results.copy()
    for column in ("Price", "Entry reference", "Stop reference", "Risk per share"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if "Risk per share" not in frame.columns:
        if {"Entry reference", "Stop reference"}.issubset(frame.columns):
            frame["Risk per share"] = (
                frame["Entry reference"] - frame["Stop reference"]
            ).abs()
        else:
            frame["Risk per share"] = float("nan")

    entry_column = (
        "Entry reference"
        if "Entry reference" in frame.columns
        else "Price"
        if "Price" in frame.columns
        else None
    )
    entry = (
        pd.to_numeric(frame[entry_column], errors="coerce")
        if entry_column is not None
        else pd.Series(float("nan"), index=frame.index, dtype=float)
    )
    risk_per_share = pd.to_numeric(frame["Risk per share"], errors="coerce")
    valid_entry = entry.gt(0) & entry.map(math.isfinite)
    valid_risk = risk_per_share.gt(0) & risk_per_share.map(
        lambda value: math.isfinite(value) if pd.notna(value) else False
    )

    frame["Risk budget"] = risk_budget
    frame["Capital limit"] = capital_limit
    risk_quantity = (risk_budget / risk_per_share.where(valid_risk)).replace(
        [float("inf"), float("-inf")], float("nan")
    ).fillna(0).floordiv(1)
    capital_quantity = (capital_limit / entry.where(valid_entry)).replace(
        [float("inf"), float("-inf")], float("nan")
    ).fillna(0).floordiv(1)
    frame["Risk-based quantity"] = risk_quantity.astype(int)
    frame["Capital-based quantity"] = capital_quantity.astype(int)
    frame["Suggested quantity"] = frame[
        ["Risk-based quantity", "Capital-based quantity"]
    ].min(axis=1).astype(int)
    frame["Planned capital"] = (entry * frame["Suggested quantity"]).fillna(0).round(2)
    frame["Planned risk"] = (
        risk_per_share * frame["Suggested quantity"]
    ).fillna(0).round(2)

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
