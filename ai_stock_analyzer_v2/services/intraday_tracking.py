"""Shared helpers for intraday setup tracking services."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pandas as pd


def copy_records(
    previous: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Copy per-symbol records without sharing nested record dictionaries."""
    return {symbol: dict(value) for symbol, value in previous.items()}


def setup_rows(
    results: pd.DataFrame,
    columns: tuple[str, ...],
) -> Iterator[tuple[Any, ...]]:
    """Yield setup rows only when the requested columns are available."""
    if results is None or results.empty:
        return iter(())

    if not set(columns).issubset(results.columns):
        return iter(())

    return results[list(columns)].itertuples(index=False, name=None)
