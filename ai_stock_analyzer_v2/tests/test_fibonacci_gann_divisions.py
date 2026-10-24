"""Tests for explicit Gann price-range divisions."""

import pytest

from modules.fibonacci_gann.gann_divisions import (
    DEFAULT_GANN_DIVISIONS,
    gann_price_divisions,
)


def test_default_divisions_include_eighths_and_endpoints() -> None:
    result = gann_price_divisions(80.0, 160.0)

    assert len(result) == 9
    assert result[0.0] == 80.0
    assert result[0.125] == 90.0
    assert result[0.5] == 120.0
    assert result[1.0] == 160.0
    assert DEFAULT_GANN_DIVISIONS == 8


def test_custom_divisions_are_evenly_spaced() -> None:
    assert gann_price_divisions(10.0, 20.0, divisions=4) == {
        0.0: 10.0,
        0.25: 12.5,
        0.5: 15.0,
        0.75: 17.5,
        1.0: 20.0,
    }


def test_descending_range_preserves_endpoint_order() -> None:
    result = gann_price_divisions(160.0, 80.0, divisions=4)

    assert result[0.0] == 160.0
    assert result[0.5] == 120.0
    assert result[1.0] == 80.0


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (float("inf"), 10.0),
        (10.0, float("nan")),
        (True, 10.0),
        ("10", 20.0),
    ],
)
def test_invalid_range_values_raise(start: object, end: object) -> None:
    with pytest.raises(ValueError):
        gann_price_divisions(start, end)  # type: ignore[arg-type]


def test_equal_range_endpoints_raise() -> None:
    with pytest.raises(ValueError, match="must differ"):
        gann_price_divisions(10.0, 10.0)


@pytest.mark.parametrize("divisions", [0, -1, True, 1.5, "8"])
def test_invalid_division_count_raises(divisions: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        gann_price_divisions(10.0, 20.0, divisions=divisions)  # type: ignore[arg-type]
