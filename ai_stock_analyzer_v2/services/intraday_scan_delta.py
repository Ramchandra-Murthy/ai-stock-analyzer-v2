"""Descriptive deltas between consecutive intraday scan snapshots."""

# ruff: isort: skip_file

from __future__ import annotations

from typing import Any

import pandas as pd

DELTA_COLUMNS = [
    "Timestamp",
    "Candidate delta",
    "Average change delta %",
    "Average volume surge delta x",
    "Exchanges",
    "Market-cap baskets",
    "New top symbols",
    "Dropped top symbols",
]


def _symbols(value: Any) -> set[str]:
    if not isinstance(value, str):
        return set()
    return {symbol.strip() for symbol in value.split(",") if symbol.strip()}


def snapshot_delta_frame(
    history: list[dict[str, Any]] | None,
    *,
    limit: int = 50,
) -> pd.DataFrame:
    """Return descriptive changes between consecutive scan snapshots."""
    snapshots = pd.DataFrame(history or [])
    if len(snapshots) < 2:
        return pd.DataFrame(columns=DELTA_COLUMNS)

    rows: list[dict[str, Any]] = []
    for previous, current in zip(
        snapshots.iloc[:-1].to_dict("records"),
        snapshots.iloc[1:].to_dict("records"),
        strict=False,
    ):
        previous_symbols = _symbols(previous.get("Top symbols"))
        current_symbols = _symbols(current.get("Top symbols"))
        rows.append(
            {
                "Timestamp": current.get("Timestamp"),
                "Candidate delta": _numeric_delta(
                    current.get("Candidates"),
                    previous.get("Candidates"),
                ),
                "Average change delta %": _numeric_delta(
                    current.get("Average change %"),
                    previous.get("Average change %"),
                ),
                "Average volume surge delta x": _numeric_delta(
                    current.get("Average volume surge x"),
                    previous.get("Average volume surge x"),
                ),
                "Exchanges": current.get("Exchanges"),
                "Market-cap baskets": current.get("Market-cap baskets"),
                "New top symbols": ", ".join(sorted(current_symbols - previous_symbols)),
                "Dropped top symbols": ", ".join(sorted(previous_symbols - current_symbols)),
            }
        )

    frame = pd.DataFrame(rows, columns=DELTA_COLUMNS)
    return frame.tail(limit).reset_index(drop=True)


def _numeric_delta(current: Any, previous: Any) -> float | None:
    current_value = pd.to_numeric(pd.Series([current]), errors="coerce").iloc[0]
    previous_value = pd.to_numeric(pd.Series([previous]), errors="coerce").iloc[0]
    if pd.isna(current_value) or pd.isna(previous_value):
        return None
    return round(float(current_value - previous_value), 2)
