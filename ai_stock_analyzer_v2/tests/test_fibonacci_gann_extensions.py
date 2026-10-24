"""Unit tests for three-anchor Fibonacci extension projections."""

import pytest

from modules.fibonacci_gann.extensions import fibonacci_extension_levels


def test_bullish_projection_matches_hand_calculated_levels() -> None:
    levels = fibonacci_extension_levels(100, 120, 110, ratios=(1.0, 1.618, 2.618))
    assert levels == pytest.approx({1.0: 130.0, 1.618: 142.36, 2.618: 162.36})


def test_bearish_projection_preserves_direction() -> None:
    levels = fibonacci_extension_levels(120, 100, 110, ratios=(1.0, 1.618))
    assert levels == pytest.approx({1.0: 90.0, 1.618: 77.64})


def test_book_discussed_default_levels_are_exposed() -> None:
    levels = fibonacci_extension_levels(100, 110, 105)
    assert tuple(levels) == pytest.approx((1.0, 1.318, 1.5, 1.618, 2.0, 2.618))


@pytest.mark.parametrize(
    "anchors",
    [
        (0, 100, 90),
        (100, 100, 90),
        (100, float("inf"), 90),
        (100, 110, float("nan")),
        (100, -110, 90),
    ],
)
def test_invalid_anchors_are_rejected(anchors: tuple[float, float, float]) -> None:
    with pytest.raises(ValueError):
        fibonacci_extension_levels(*anchors)


@pytest.mark.parametrize("ratios", [(0,), (-1,), (float("inf"),), (1, 1), ()])
def test_invalid_ratios_are_rejected(ratios: tuple[float, ...]) -> None:
    with pytest.raises(ValueError):
        fibonacci_extension_levels(100, 110, 105, ratios=ratios)
