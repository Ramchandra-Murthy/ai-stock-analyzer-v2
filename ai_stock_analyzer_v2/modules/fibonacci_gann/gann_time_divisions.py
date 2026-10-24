"""Explicit bar-index interval divisions for Gann-style research.

Positions are arithmetic reference points only; this helper does not infer
market cycles or claim that projected dates or bars are predictive.
"""

from __future__ import annotations

from modules.fibonacci_gann._division_utils import validate_division_interval

DEFAULT_GANN_TIME_DIVISIONS = 8


def gann_time_divisions(
    start_bar: int | float,
    end_bar: int | float,
    *,
    divisions: int = DEFAULT_GANN_TIME_DIVISIONS,
) -> dict[float, float]:
    """Return equally spaced bar positions keyed by fractional interval.

    Endpoints are caller-supplied bar indices or positions. The order is
    preserved, so descending intervals are supported. Intermediate positions
    can be fractional when the interval is not evenly divisible into whole bars.
    """
    start, span = validate_division_interval(
        start_bar,
        end_bar,
        start_name="start_bar",
        end_name="end_bar",
        divisions=divisions,
    )
    return {index / divisions: start + span * index / divisions for index in range(divisions + 1)}
