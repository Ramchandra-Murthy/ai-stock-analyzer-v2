"""Tests for explicit Gann angle level calculations."""

import pytest

from modules.fibonacci_gann.gann_angles import (
    DEFAULT_GANN_SLOPES,
    gann_angle_levels,
)


def test_default_slopes_project_from_anchor() -> None:
    result = gann_angle_levels(100.0, 10, 14)

    assert result == {1.0: 104.0, 0.5: 102.0, 2.0: 108.0}
    assert DEFAULT_GANN_SLOPES == (1.0, 0.5, 2.0)


def test_negative_slope_falls_over_time() -> None:
    assert gann_angle_levels(100.0, 10, 12, slopes=(-1.5,)) == {-1.5: 97.0}


def test_earlier_target_bar_uses_signed_bar_delta() -> None:
    assert gann_angle_levels(100.0, 10, 8, slopes=(2.0,)) == {2.0: 96.0}


def test_target_at_anchor_returns_anchor_price() -> None:
    assert gann_angle_levels(100.0, 10, 10, slopes=(1.0,)) == {1.0: 100.0}


@pytest.mark.parametrize("price", [0, -1, float("inf"), float("nan"), True, "100"])
def test_invalid_anchor_price_raises(price: object) -> None:
    with pytest.raises(ValueError, match="anchor_price"):
        gann_angle_levels(price, 0, 1)  # type: ignore[arg-type]


@pytest.mark.parametrize("bar", [True, 1.5, "2"])
def test_invalid_bar_indices_raise(bar: object) -> None:
    with pytest.raises(ValueError, match="bar indices"):
        gann_angle_levels(100.0, bar, 2)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "slopes",
    [(), (1.0, 1.0), (float("inf"),), (float("nan"),), (True,), ("1",)],
)
def test_invalid_slopes_raise(slopes: tuple[object, ...]) -> None:
    with pytest.raises(ValueError):
        gann_angle_levels(100.0, 0, 1, slopes=slopes)  # type: ignore[arg-type]
