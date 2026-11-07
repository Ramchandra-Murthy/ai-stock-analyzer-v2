"""Tests for intraday position sizing."""

from services.intraday_position_sizing import calculate_position_size


def test_long_position_size_is_capped_by_risk_and_capital():
    result = calculate_position_size(100000, 1, 100, 98, 104, "LONG")
    assert result.risk_amount == 1000
    assert result.risk_quantity == 500
    assert result.capital_quantity == 1000
    assert result.quantity == 500
    assert result.planned_risk == 1000
    assert result.planned_reward == 2000
    assert result.planned_rr == 2


def test_short_position_size_and_reward():
    result = calculate_position_size(50000, 2, 200, 205, 190, "SHORT")
    assert result.risk_amount == 1000
    assert result.quantity == 200
    assert result.planned_risk == 1000
    assert result.planned_reward == 2000
    assert result.planned_rr == 2


import pytest


@pytest.mark.parametrize(
    "values",
    [
        (float("nan"), 1, 100, 98, 104, "LONG"),
        (100000, float("inf"), 100, 98, 104, "LONG"),
        (100000, 1, float("-inf"), 98, 104, "LONG"),
    ],
)
def test_rejects_non_finite_inputs(values):
    with pytest.raises(ValueError, match="finite"):
        calculate_position_size(*values)


@pytest.mark.parametrize(
    "values",
    [
        (100000, -1, 100, 98, 104, "LONG"),
        (100000, 101, 100, 98, 104, "LONG"),
        (100000, 1, 0, 98, 104, "LONG"),
        (100000, 1, 100, 100, 104, "LONG"),
        (100000, 1, 100, 98, 98, "LONG"),
        (100000, 1, 100, 102, 104, "LONG"),
        (100000, 1, 100, 98, 104, "SIDEWAYS"),
    ],
)
def test_rejects_invalid_levels_and_controls(values):
    import pytest

    with pytest.raises(ValueError):
        calculate_position_size(*values)


def test_zero_risk_budget_produces_zero_quantity():
    result = calculate_position_size(100000, 0, 100, 98, 104, "LONG")
    assert result.quantity == 0
    assert result.planned_risk == 0
    assert result.planned_rr is None


def test_short_levels_are_validated_and_sized():
    result = calculate_position_size(50000, 2, 200, 205, 190, "SHORT")
    assert result.quantity == 200
    assert result.planned_reward == 2000
    assert result.planned_rr == 2
