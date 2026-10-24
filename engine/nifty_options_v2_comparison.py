"""Comparison helpers for NIFTY Options Book V2 published baselines."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class BookSeriesResult:
    """Published book result for one series."""

    series: str
    points: float


@dataclass(frozen=True)
class ComparisonRow:
    """Difference between a book result and an actual backtest result."""

    series: str
    book_points: float
    actual_points: float
    difference_points: float


def compare_series(
    book_results: Sequence[BookSeriesResult],
    actual_results: Sequence[BookSeriesResult],
) -> list[ComparisonRow]:
    """Compare matching series without inventing missing observations."""
    book = {item.series: item.points for item in book_results}
    actual = {item.series: item.points for item in actual_results}
    if set(book) != set(actual):
        missing_from_actual = sorted(set(book) - set(actual))
        missing_from_book = sorted(set(actual) - set(book))
        raise ValueError(
            "series sets differ: "
            f"missing_from_actual={missing_from_actual}, "
            f"missing_from_book={missing_from_book}"
        )
    return [
        ComparisonRow(
            series=series,
            book_points=book[series],
            actual_points=actual[series],
            difference_points=actual[series] - book[series],
        )
        for series in sorted(book)
    ]


def total_points(results: Sequence[BookSeriesResult]) -> float:
    """Return cumulative points for a supplied result set."""
    return sum(item.points for item in results)
