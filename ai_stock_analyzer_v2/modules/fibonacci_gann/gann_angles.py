"""Explicit Gann angle price calculations for research use.

The helper applies caller-supplied price-units-per-bar slopes to an anchor.
It does not infer market pivots or impose a universal chart scale: a 1:1
angle depends on the chosen price and time units, so outputs are geometric
reference levels rather than trading signals or predictions.
"""

from __future__ import annotations

from collections.abc import Iterable
from math import isfinite

DEFAULT_GANN_SLOPES: tuple[float, ...] = (1.0, 0.5, 2.0)


def gann_angle_levels(
    anchor_price: float,
    anchor_bar: int,
    target_bar: int,
    *,
    slopes: Iterable[float] = DEFAULT_GANN_SLOPES,
) -> dict[float, float]:
    """Return price levels at target_bar for explicit signed slopes.

    Each slope is measured in price units per bar. Positive slopes rise as
    bar index increases; negative slopes fall. The anchor and target bars may
    be in either order, allowing the same formula to evaluate earlier bars.
    """
    if (
        isinstance(anchor_price, bool)
        or not isinstance(anchor_price, (int, float))
        or not isfinite(anchor_price)
        or anchor_price <= 0
    ):
        raise ValueError("anchor_price must be a finite positive number")
    if (
        isinstance(anchor_bar, bool)
        or not isinstance(anchor_bar, int)
        or isinstance(target_bar, bool)
        or not isinstance(target_bar, int)
    ):
        raise ValueError("bar indices must be integers")

    slope_values = tuple(slopes)
    if not slope_values:
        raise ValueError("at least one slope is required")
    if any(
        isinstance(slope, bool) or not isinstance(slope, (int, float)) or not isfinite(slope)
        for slope in slope_values
    ):
        raise ValueError("slopes must be finite numbers")
    if len(set(slope_values)) != len(slope_values):
        raise ValueError("slopes must be unique")

    bar_delta = target_bar - anchor_bar
    return {float(slope): float(anchor_price) + float(slope) * bar_delta for slope in slope_values}
