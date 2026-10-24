"""Internal validation shared by deterministic interval-division helpers."""

from __future__ import annotations

from math import isfinite


def validate_division_interval(
    start_value: int | float,
    end_value: int | float,
    *,
    start_name: str,
    end_name: str,
    divisions: int,
) -> tuple[float, float]:
    """Validate an interval and return its floating-point start and span."""
    for name, value in ((start_name, start_value), (end_name, end_value)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError(f"{name} must be a finite number")
    if start_value == end_value:
        raise ValueError(f"{start_name} and {end_name} must differ")
    if isinstance(divisions, bool) or not isinstance(divisions, int) or divisions < 1:
        raise ValueError("divisions must be a positive integer")

    start = float(start_value)
    return start, float(end_value) - start
