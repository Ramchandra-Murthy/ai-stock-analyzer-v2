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
