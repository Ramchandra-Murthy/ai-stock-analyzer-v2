"""Fibonacci time-interval projections for research use.

This helper returns future bar indices at selected positive Fibonacci intervals
from an explicitly supplied anchor bar. It does not infer pivots or predict
market direction; projected positions are reference windows, not guaranteed
turning points.
"""

from __future__ import annotations

from collections.abc import Iterable

DEFAULT_TIMELINE_INTERVALS: tuple[int, ...] = (1, 2, 3, 5, 8, 13, 21, 34, 55, 89)


def fibonacci_timeline_levels(
    anchor_bar: int,
    *,
    intervals: Iterable[int] = DEFAULT_TIMELINE_INTERVALS,
) -> tuple[int, ...]:
    """Return future bar indices at Fibonacci intervals after the anchor.

    anchor_bar is a consistently indexed bar position supplied by the caller.
    Each returned position is anchor_bar + interval. Calendar-time conversion
    and pivot detection are intentionally outside this pure helper.
    """
    if isinstance(anchor_bar, bool) or not isinstance(anchor_bar, int):
        raise ValueError("anchor_bar must be an integer bar index")

    interval_values = tuple(intervals)
    if not interval_values:
        raise ValueError("at least one timeline interval is required")
    if any(
        isinstance(interval, bool) or not isinstance(interval, int) or interval <= 0
        for interval in interval_values
    ):
        raise ValueError("timeline intervals must be positive integers")
    if len(set(interval_values)) != len(interval_values):
        raise ValueError("timeline intervals must be unique")

    return tuple(anchor_bar + interval for interval in interval_values)
