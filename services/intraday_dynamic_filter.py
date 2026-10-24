"""Helpers for dynamic filtering of current intraday candidates."""

from __future__ import annotations

import pandas as pd


def filter_intraday_candidates(
    results: pd.DataFrame,
    direction: str = "All",
    setup_state: str = "All",
    exchange: str = "All",
    minimum_score: float = 0.0,
    limit: int = 20,
) -> pd.DataFrame:
    """Filter the latest scan without changing the underlying scan data."""
    if results is None or results.empty:
        return pd.DataFrame(columns=results.columns if results is not None else None)

    filtered = results.copy()
    if direction != "All" and "Direction" in filtered.columns:
        filtered = filtered[filtered["Direction"].eq(direction)]
    if setup_state != "All" and "Plan state" in filtered.columns:
        filtered = filtered[filtered["Plan state"].eq(setup_state)]
    if exchange != "All" and "Exchange" in filtered.columns:
        filtered = filtered[filtered["Exchange"].eq(exchange)]
    if "Composite score" in filtered.columns:
        filtered = filtered[
            pd.to_numeric(filtered["Composite score"], errors="coerce").fillna(0) >= minimum_score
        ]

    sort_columns = [
        column
        for column in ("Composite score", "Opportunity score", "5-min change %")
        if column in filtered.columns
    ]
    if sort_columns:
        filtered = filtered.sort_values(
            sort_columns,
            ascending=[False] * len(sort_columns),
            na_position="last",
        )

    return filtered.head(max(1, int(limit))).reset_index(drop=True)
