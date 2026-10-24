"""Universe refinement for NSE/BSE algorithmic research.

Chapter 7 emphasizes refining the investment universe with liquidity, crowded-short, dividend/buyback, fundamental, valuation, beta, sector-return and beta-momentum information. This module provides a data-source-neutral implementation so the existing NSE/BSE universe can be filtered without changing the live scanner.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class UniverseCriteria:
    """Optional thresholds for refining an NSE/BSE candidate universe."""

    min_price: float = 0.0
    min_avg_volume: float = 0.0
    min_avg_turnover: float = 0.0
    max_beta: float | None = None
    min_relative_return_pct: float | None = None


def refine_universe(
    universe: pd.DataFrame,
    criteria: UniverseCriteria | None = None,
) -> pd.DataFrame:
    """Return candidates that satisfy the supplied observable filters."""
    if "symbol" not in universe.columns:
        raise ValueError("universe must contain a symbol column")

    criteria = criteria or UniverseCriteria()
    result = universe.copy()
    filters: list[pd.Series] = []

    if criteria.min_price > 0:
        filters.append(_numeric(result, "price") >= criteria.min_price)
    if criteria.min_avg_volume > 0:
        filters.append(_numeric(result, "avg_volume") >= criteria.min_avg_volume)
    if criteria.min_avg_turnover > 0:
        filters.append(_numeric(result, "avg_turnover") >= criteria.min_avg_turnover)
    if criteria.max_beta is not None and "beta" in result.columns:
        filters.append(_numeric(result, "beta") <= criteria.max_beta)
    if criteria.min_relative_return_pct is not None and "relative_return_pct" in result.columns:
        filters.append(_numeric(result, "relative_return_pct") >= criteria.min_relative_return_pct)

    for mask in filters:
        result = result.loc[mask.loc[result.index]]
    return result.reset_index(drop=True)


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        raise ValueError(f"missing required column for selected filter: {column}")
    return pd.to_numeric(frame[column], errors="coerce").fillna(0.0)


def candidate_table(symbols: list[str], exchange: str) -> pd.DataFrame:
    """Create a normalized candidate table for NSE or BSE symbols."""
    exchange = exchange.upper()
    if exchange not in {"NSE", "BSE"}:
        raise ValueError("exchange must be NSE or BSE")
    return pd.DataFrame({"symbol": symbols, "exchange": exchange})
