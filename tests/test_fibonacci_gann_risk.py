"""Tests for conservative Fibonacci/Gann position sizing."""

from decimal import Decimal

import pytest

from modules.fibonacci_gann.risk import calculate_position_size


def test_size_respects_risk_and_capital_limits() -> None:
    result = calculate_position_size(
        "100", "95", capital="10000", max_loss="500", cost_per_unit="1"
    )
    assert result.quantity == 83
    assert result.estimated_loss == Decimal("498")
    assert result.capital_required == Decimal("8300")
    assert result.estimated_loss <= result.risk_limit
    assert result.capital_required <= result.capital_limit


def test_capital_limit_can_be_tighter_than_risk_limit() -> None:
    result = calculate_position_size("6000", "5900", capital="10000", max_loss="500")
    assert result.quantity == 1
    assert result.capital_required == Decimal("6000")
    assert result.estimated_loss == Decimal("100")


def test_costs_reduce_position_size() -> None:
    no_cost = calculate_position_size(100, 95, capital=10000, max_loss=500)
    with_cost = calculate_position_size(100, 95, capital=10000, max_loss=500, cost_per_unit=2)
    assert with_cost.quantity < no_cost.quantity


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"entry_price": 100, "stop_price": 100}, "below entry"),
        ({"entry_price": 100, "stop_price": 101}, "below entry"),
        ({"entry_price": 0, "stop_price": 1}, "entry_price"),
        ({"entry_price": 100, "stop_price": 95, "capital": 0}, "capital"),
        ({"entry_price": 100, "stop_price": 95, "max_loss": 0}, "max_loss"),
        ({"entry_price": 100, "stop_price": 95, "cost_per_unit": -1}, "cost_per_unit"),
        ({"entry_price": 100, "stop_price": 95, "capital": 100, "max_loss": 101}, "cannot exceed"),
    ],
)
def test_invalid_inputs_are_rejected(kwargs: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        calculate_position_size(**kwargs)


def test_rejects_trade_when_one_unit_exceeds_risk_limit() -> None:
    with pytest.raises(ValueError, match="even one unit"):
        calculate_position_size(1000, 900, capital=10000, max_loss=50)


def test_decimal_inputs_are_preserved() -> None:
    result = calculate_position_size(Decimal("10.5"), Decimal("10"), capital=100, max_loss=5)
    assert result.estimated_loss == Decimal("4.5")
    assert result.estimated_loss <= result.risk_limit
    assert result.quantity == 9


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        (field, value)
        for field in ("entry_price", "stop_price", "capital", "max_loss", "cost_per_unit")
        for value in ("NaN", "Infinity", "invalid", True, None)
    ],
)
def test_all_position_sizing_inputs_reject_malformed_values(
    field: str, invalid_value: object
) -> None:
    kwargs: dict[str, object] = {
        "entry_price": 100,
        "stop_price": 95,
        "capital": 1000,
        "max_loss": 100,
        "cost_per_unit": 0,
    }
    kwargs[field] = invalid_value

    with pytest.raises(ValueError):
        calculate_position_size(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("entry", "stop", "capital", "max_loss", "cost", "expected_quantity"),
    [
        (100, 95, 3000, 100, 0, 20),
        (100, 95, 3000, 99, 0, 19),
        (100, 95, 3000, 100, 1, 16),
        (100, 95, 199, 100, 0, 1),
        (100, 95, 200, 100, 0, 2),
    ],
)
def test_position_size_flooring_at_risk_and_capital_boundaries(
    entry: int,
    stop: int,
    capital: int,
    max_loss: int,
    cost: int,
    expected_quantity: int,
) -> None:
    result = calculate_position_size(
        entry, stop, capital=capital, max_loss=max_loss, cost_per_unit=cost
    )

    assert result.quantity == expected_quantity
    assert result.estimated_loss <= result.risk_limit
    assert result.capital_required <= result.capital_limit
    assert result.estimated_loss + (result.risk_per_unit) > result.risk_limit or (
        result.capital_required + result.entry_price > result.capital_limit
    )
