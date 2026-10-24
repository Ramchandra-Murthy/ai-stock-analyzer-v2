"""Fibonacci fanline (speedline) calculations for research use.

MacLean's *Fibonacci and Gann Applications in Financial Markets*, Chapter 3,
describes plotting 38.2%, 50%, and 61.8% retracement points on the vertical
side of the move's right triangle, drawing lines from the origin through those
points, then extending the lines through time. This module implements that
geometry for explicitly supplied origin/extreme prices and elapsed-bar counts.
It does not infer pivots or make trading decisions.
"""

from __future__ import annotations

from collections.abc import Iterable
from math import isfinite

DEFAULT_FANLINE_RATIOS: tuple[float, ...] = (0.382, 0.5, 0.618)


def fibonacci_fanline_levels(
    origin_price: float,
    extreme_price: float,
    elapsed_bars: float,
    move_bars: float,
    *,
    ratios: Iterable[float] = DEFAULT_FANLINE_RATIOS,
) -> dict[float, float]:
    """Return fanline prices at the requested elapsed-bar distance.

    move_bars is the bar distance from origin to the move's extreme. For each
    retracement ratio r, the line passes through the origin and the point
    extreme_price - (extreme_price - origin_price) * r at move_bars.
    Lines are extended linearly beyond that point in time.
    """
    values = (origin_price, extreme_price, elapsed_bars, move_bars)
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value)
        for value in values
    ):
        raise ValueError("prices and bar counts must be finite numbers")
    if origin_price <= 0 or extreme_price <= 0:
        raise ValueError("prices must be positive")
    if origin_price == extreme_price:
        raise ValueError("origin_price and extreme_price must differ")
    if elapsed_bars < 0:
        raise ValueError("elapsed_bars must be non-negative")
    if move_bars <= 0:
        raise ValueError("move_bars must be positive")

    ratio_values = tuple(ratios)
    if not ratio_values:
        raise ValueError("at least one fanline ratio is required")
    if any(
        isinstance(ratio, bool)
        or not isinstance(ratio, (int, float))
        or not isfinite(ratio)
        or not 0 < ratio < 1
        for ratio in ratio_values
    ):
        raise ValueError("fanline ratios must be finite numbers between 0 and 1")
    if len(set(ratio_values)) != len(ratio_values):
        raise ValueError("fanline ratios must be unique")

    move = float(extreme_price) - float(origin_price)
    time_fraction = float(elapsed_bars) / float(move_bars)
    return {
        float(ratio): float(origin_price) + (move * (1.0 - float(ratio))) * time_fraction
        for ratio in ratio_values
    }
