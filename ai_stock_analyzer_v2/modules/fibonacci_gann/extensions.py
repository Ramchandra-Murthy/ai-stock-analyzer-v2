"""Three-anchor Fibonacci price projections for research use.

The uploaded MacLean book discusses extension levels including 131.8%, 150%,
161.8%, 200%, and 261.8% (Chapter 2; later examples in Chapters 5 and 8).
This helper implements a transparent three-anchor projection convention:
A = start of impulse, B = end of impulse, C = end of pullback, and
target(r) = C + (B - A) * r. It is an explicit engineering convention, not
a claim that every anchor convention in the book is identical to this one.
These levels are descriptive research references, not forecasts or trade advice.
"""

from __future__ import annotations

from collections.abc import Iterable
from math import isfinite

DEFAULT_EXTENSION_RATIOS: tuple[float, ...] = (1.0, 1.318, 1.5, 1.618, 2.0, 2.618)


def fibonacci_extension_levels(
    impulse_start: float,
    impulse_end: float,
    pullback_end: float,
    *,
    ratios: Iterable[float] = DEFAULT_EXTENSION_RATIOS,
) -> dict[float, float]:
    """Return three-anchor Fibonacci price projections keyed by ratio.

    The signed impulse (impulse_end - impulse_start) preserves direction:
    bullish projections extend above pullback_end; bearish projections extend
    below it. Anchors must be finite, positive prices and the impulse must be
    non-zero. Ratios must be finite, positive, and unique.
    """
    anchors = (impulse_start, impulse_end, pullback_end)
    if not all(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
        and value > 0
        for value in anchors
    ):
        raise ValueError("anchors must be finite, positive prices")
    impulse = float(impulse_end) - float(impulse_start)
    if impulse == 0:
        raise ValueError("impulse_start and impulse_end must differ")

    ratio_values = tuple(ratios)
    if not ratio_values:
        raise ValueError("at least one extension ratio is required")
    if any(
        isinstance(ratio, bool)
        or not isinstance(ratio, (int, float))
        or not isfinite(ratio)
        or ratio <= 0
        for ratio in ratio_values
    ):
        raise ValueError("extension ratios must be finite positive numbers")
    if len(set(ratio_values)) != len(ratio_values):
        raise ValueError("extension ratios must be unique")

    return {float(ratio): float(pullback_end) + impulse * float(ratio) for ratio in ratio_values}
