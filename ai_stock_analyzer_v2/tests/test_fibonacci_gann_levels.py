"""Tests for the isolated Fibonacci and Gann calculation helpers."""

from decimal import Decimal

import pytest

from modules.fibonacci_gann.levels import (
    fibonacci_extensions,
    fibonacci_retracements,
    gann_eighths,
)


def test_fibonacci_retracements_for_example_swing() -> None:
    levels = fibonacci_retracements(800, 1000)

    assert levels["23.6%"] == Decimal("952.800")
    assert levels["38.2%"] == Decimal("923.600")
    assert levels["50.0%"] == Decimal("900.000")
    assert levels["61.8%"] == Decimal("876.400")


def test_fibonacci_extensions_for_example_swing() -> None:
    levels = fibonacci_extensions(800, 1000)

    assert levels["1.000x"] == Decimal("1200.000")
    assert levels["1.272x"] == Decimal("1254.400")
    assert levels["1.618x"] == Decimal("1323.600")


def test_gann_eighths_include_endpoints_and_midpoint() -> None:
    levels = gann_eighths(800, 1000)

    assert len(levels) == 9
    assert levels["0/8"] == Decimal("800")
    assert levels["4/8"] == Decimal("900")
    assert levels["8/8"] == Decimal("1000")


@pytest.mark.parametrize(
    ("low", "high"),
    [(0, 100), (-1, 100), (100, 100), (200, 100), ("NaN", 100)],
)
def test_invalid_swings_are_rejected(low: int | str, high: int) -> None:
    with pytest.raises(ValueError):
        fibonacci_retracements(low, high)


def test_non_finite_high_is_rejected() -> None:
    with pytest.raises(ValueError):
        gann_eighths(100, "Infinity")


@pytest.mark.parametrize(
    "calculator",
    [fibonacci_retracements, fibonacci_extensions, gann_eighths],
)
@pytest.mark.parametrize(
    ("low", "high"),
    [
        ("NaN", 100),
        (100, "Infinity"),
        ("invalid", 100),
        (100, "invalid"),
        (True, 100),
        (100, None),
    ],
)
def test_all_level_calculators_reject_invalid_prices(
    calculator: object, low: object, high: object
) -> None:
    with pytest.raises(ValueError):
        calculator(low, high)  # type: ignore[operator]


@pytest.mark.parametrize(
    "calculator",
    [fibonacci_retracements, fibonacci_extensions, gann_eighths],
)
@pytest.mark.parametrize(("low", "high"), [(100, 100), (200, 100)])
def test_all_level_calculators_reject_non_increasing_swings(
    calculator: object, low: int, high: int
) -> None:
    with pytest.raises(ValueError):
        calculator(low, high)  # type: ignore[operator]
