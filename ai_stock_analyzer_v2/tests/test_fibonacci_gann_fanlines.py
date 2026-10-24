"""Unit tests for Fibonacci fanline geometry."""

import pytest

from modules.fibonacci_gann.fanlines import fibonacci_fanline_levels


def test_bullish_fanlines_reach_retracement_points() -> None:
    levels = fibonacci_fanline_levels(100, 120, elapsed_bars=10, move_bars=10)
    assert levels == pytest.approx({0.382: 112.36, 0.5: 110.0, 0.618: 107.64})


def test_bearish_fanlines_reach_retracement_points() -> None:
    levels = fibonacci_fanline_levels(120, 100, elapsed_bars=10, move_bars=10)
    assert levels == pytest.approx({0.382: 107.64, 0.5: 110.0, 0.618: 112.36})


def test_fanlines_start_at_origin_when_elapsed_is_zero() -> None:
    levels = fibonacci_fanline_levels(100, 120, elapsed_bars=0, move_bars=10)
    assert levels == pytest.approx({0.382: 100.0, 0.5: 100.0, 0.618: 100.0})


def test_fanlines_extend_linearly_beyond_move_duration() -> None:
    levels = fibonacci_fanline_levels(100, 120, elapsed_bars=20, move_bars=10, ratios=(0.5,))
    assert levels[0.5] == pytest.approx(120.0)


@pytest.mark.parametrize(
    ("origin", "extreme", "elapsed", "duration"),
    [
        (0, 120, 10, 10),
        (100, 100, 10, 10),
        (100, float("inf"), 10, 10),
        (100, 120, -1, 10),
        (100, 120, 10, 0),
        (100, 120, 10, float("nan")),
        (True, 120, 10, 10),
    ],
)
def test_invalid_inputs_are_rejected(
    origin: float, extreme: float, elapsed: float, duration: float
) -> None:
    with pytest.raises(ValueError):
        fibonacci_fanline_levels(origin, extreme, elapsed, duration)


@pytest.mark.parametrize("ratios", [(0,), (1,), (-0.1,), (float("inf"),), (0.5, 0.5), ()])
def test_invalid_ratios_are_rejected(ratios: tuple[float, ...]) -> None:
    with pytest.raises(ValueError):
        fibonacci_fanline_levels(100, 120, 5, 10, ratios=ratios)
