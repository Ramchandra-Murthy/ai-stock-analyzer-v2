"""Tests for shared Gann interval validation."""

import math

import pytest

from modules.fibonacci_gann._division_utils import validate_division_interval


def test_returns_start_and_signed_span() -> None:
    assert validate_division_interval(10, 2, start_name="start", end_name="end", divisions=4) == (
        10.0,
        -8.0,
    )


@pytest.mark.parametrize("value", [True, False, math.nan, math.inf, -math.inf, "3"])
def test_rejects_non_finite_or_non_numeric_endpoints(value: object) -> None:
    with pytest.raises(ValueError):
        validate_division_interval(
            value, 10, start_name="start", end_name="end", divisions=4  # type: ignore[arg-type]
        )


def test_rejects_equal_endpoints() -> None:
    with pytest.raises(ValueError, match="must differ"):
        validate_division_interval(5, 5, start_name="start", end_name="end", divisions=4)


@pytest.mark.parametrize("divisions", [True, False, 0, -1, 1.5])
def test_rejects_invalid_division_count(divisions: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        validate_division_interval(
            0, 10, start_name="start", end_name="end", divisions=divisions  # type: ignore[arg-type]
        )
