"""Tests for explicit Gann-style time interval divisions."""

import pytest

from modules.fibonacci_gann.gann_time_divisions import gann_time_divisions


def test_default_divisions_include_both_endpoints() -> None:
    levels = gann_time_divisions(0, 80)

    assert len(levels) == 9
    assert levels[0.0] == 0.0
    assert levels[0.5] == 40.0
    assert levels[1.0] == 80.0


def test_custom_divisions_and_fractional_positions() -> None:
    levels = gann_time_divisions(10, 20, divisions=4)

    assert levels == {0.0: 10.0, 0.25: 12.5, 0.5: 15.0, 0.75: 17.5, 1.0: 20.0}


def test_descending_interval_preserves_endpoint_order() -> None:
    levels = gann_time_divisions(80, 0, divisions=4)

    assert levels[0.0] == 80.0
    assert levels[0.5] == 40.0
    assert levels[1.0] == 0.0


@pytest.mark.parametrize(
    ("start_bar", "end_bar"),
    [(3, 3), (float("nan"), 4), (2, float("inf")), (True, 5), (0, "10")],
)
def test_invalid_interval_endpoints_raise(start_bar: int | float, end_bar: int | float) -> None:
    with pytest.raises(ValueError):
        gann_time_divisions(start_bar, end_bar)


@pytest.mark.parametrize("divisions", [0, -1, 1.5, True, "8"])
def test_invalid_division_counts_raise(divisions: int) -> None:
    with pytest.raises(ValueError):
        gann_time_divisions(0, 8, divisions=divisions)
