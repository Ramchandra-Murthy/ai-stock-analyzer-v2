"""Unit tests for Fibonacci timeline projections."""

import pytest

from modules.fibonacci_gann.timelines import fibonacci_timeline_levels


def test_default_fibonacci_timeline_offsets() -> None:
    assert fibonacci_timeline_levels(100) == (101, 102, 103, 105, 108, 113, 121, 134, 155, 189)


def test_custom_timeline_intervals_preserve_order() -> None:
    assert fibonacci_timeline_levels(20, intervals=(3, 8, 13)) == (23, 28, 33)


def test_negative_anchor_index_is_supported() -> None:
    assert fibonacci_timeline_levels(-5, intervals=(1, 2)) == (-4, -3)


@pytest.mark.parametrize("anchor_bar", [True, 1.5, "10", float("inf"), float("nan")])
def test_invalid_anchor_bar_is_rejected(anchor_bar: object) -> None:
    with pytest.raises(ValueError):
        fibonacci_timeline_levels(anchor_bar)  # type: ignore[arg-type]


@pytest.mark.parametrize("intervals", [(), (0,), (-1,), (1.5,), (True,), (2, 2)])
def test_invalid_intervals_are_rejected(intervals: tuple[object, ...]) -> None:
    with pytest.raises(ValueError):
        fibonacci_timeline_levels(10, intervals=intervals)  # type: ignore[arg-type]
