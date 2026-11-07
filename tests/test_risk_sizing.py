import math

import pytest

from algorithmic_trading.risk_sizing import (
    atr_stop,
    fractional_kelly,
    kelly_fraction,
    risk_based_quantity,
)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_kelly_fraction_rejects_non_finite_inputs(value):
    with pytest.raises(ValueError, match="finite"):
        kelly_fraction(value, 2.0)
    with pytest.raises(ValueError, match="finite"):
        kelly_fraction(0.5, value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_fractional_kelly_rejects_non_finite_controls(value):
    with pytest.raises(ValueError, match="finite"):
        fractional_kelly(0.5, 2.0, fraction=value)
    with pytest.raises(ValueError, match="finite"):
        fractional_kelly(0.5, 2.0, cap=value)


@pytest.mark.parametrize("field", ["capital", "risk_pct", "entry", "stop", "max_position_pct"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_risk_based_quantity_rejects_non_finite_inputs(field, value):
    inputs = {
        "capital": 100_000.0,
        "risk_pct": 0.01,
        "entry": 500.0,
        "stop": 490.0,
        "max_position_pct": 1.0,
    }
    inputs[field] = value
    with pytest.raises(ValueError, match="finite"):
        risk_based_quantity(**inputs)


@pytest.mark.parametrize("lot_size", [0, -1, 1.5, True])
def test_risk_based_quantity_requires_positive_integer_lot_size(lot_size):
    with pytest.raises(ValueError, match="lot_size"):
        risk_based_quantity(100_000, 0.01, 500, 490, lot_size=lot_size)


def test_risk_based_quantity_keeps_risk_and_notional_caps():
    result = risk_based_quantity(
        100_000,
        0.01,
        500,
        490,
        lot_size=10,
        max_position_pct=0.5,
    )
    assert result["quantity"] == 100.0
    assert result["notional"] == 50_000.0
    assert result["risk_amount"] == 1_000.0


@pytest.mark.parametrize(
    "values",
    [
        (float("nan"), 2.0, 2.0),
        (100.0, float("inf"), 2.0),
        (100.0, 2.0, float("-inf")),
    ],
)
def test_atr_stop_rejects_non_finite_inputs(values):
    with pytest.raises(ValueError, match="finite"):
        atr_stop(*values)


def test_kelly_fraction_rejects_non_numeric_input():
    with pytest.raises(ValueError, match="finite"):
        kelly_fraction(math.nan, 2.0)
