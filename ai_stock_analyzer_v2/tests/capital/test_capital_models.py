"""
==========================================================
CAPITAL COST MODELS TEST SUITE
Module  : tests.capital.test_capital_models
Layer   : Tests / Capital / Models
==========================================================
"""

from __future__ import annotations

from services.capital.models import (
    CapitalStructure,
    CostOfDebtResult,
    CostOfEquityResult,
    WACCResult,
)


def test_capital_structure_weights() -> None:
    """Test capital structure weight and total capital calculations."""
    cs = CapitalStructure(total_debt=400.0, total_equity=600.0)

    assert cs.total_capital == 1000.0
    assert cs.debt_weight == 0.4
    assert cs.equity_weight == 0.6


def test_capital_structure_zero_division() -> None:
    """Test capital structure weight handling when total capital is zero."""
    cs = CapitalStructure(total_debt=0.0, total_equity=0.0)

    assert cs.total_capital == 0.0
    assert cs.debt_weight == 0.0
    assert cs.equity_weight == 0.0


def test_cost_of_equity_serialization() -> None:
    """Test CostOfEquityResult dictionary serialization."""
    coe = CostOfEquityResult(
        risk_free_rate=0.07,
        beta=1.2,
        equity_risk_premium=0.06,
        cost_of_equity=0.142,
    )

    serialized = coe.to_dict()
    assert serialized["risk_free_rate"] == 0.07
    assert serialized["beta"] == 1.2
    assert serialized["cost_of_equity"] == 0.142


def test_wacc_result_serialization() -> None:
    """Test WACCResult aggregation and dictionary serialization."""
    cs = CapitalStructure(total_debt=300.0, total_equity=700.0)
    coe = CostOfEquityResult(0.07, 1.1, 0.06, 0.136)
    cod = CostOfDebtResult(0.08, 0.25, 0.06)

    wacc_res = WACCResult(
        symbol="TEST",
        capital_structure=cs,
        cost_of_equity=coe,
        cost_of_debt=cod,
        wacc=0.1132,
    )

    serialized = wacc_res.to_dict()
    assert serialized["symbol"] == "TEST"
    assert serialized["capital_structure"]["debt_weight"] == 0.3
    assert serialized["wacc"] == 0.1132
