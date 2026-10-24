"""Explicit price-range divisions for Gann-style research.

This helper divides a caller-supplied range into equal fractional intervals.
It does not infer trading ranges or claim that any level is predictive.
"""

from __future__ import annotations

from modules.fibonacci_gann._division_utils import validate_division_interval

DEFAULT_GANN_DIVISIONS = 8


def gann_price_divisions(
    range_start: float,
    range_end: float,
    *,
    divisions: int = DEFAULT_GANN_DIVISIONS,
) -> dict[float, float]:
    """Return equally spaced price levels keyed by fractional position.

    The returned keys run from 0.0 through 1.0 inclusive. The endpoints
    preserve the supplied order, so descending ranges are supported too.
    """
    start, span = validate_division_interval(
        range_start,
        range_end,
        start_name="range_start",
        end_name="range_end",
        divisions=divisions,
    )
    return {index / divisions: start + span * index / divisions for index in range(divisions + 1)}
