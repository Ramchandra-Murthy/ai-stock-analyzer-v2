"""
==========================================================
UNIT TEST SUITE - CAPITAL COST ENGINE (WACC)
Module  : tests.wacc.test_wacc_service
==========================================================
"""

from services.wacc.wacc_models import BetaAdjustmentInput, CAPMInput, WACCInput
from services.wacc.wacc_service import CapitalCostEngine


def test_capm_cost_of_equity_calculation():
    engine = CapitalCostEngine()
    capm_in = CAPMInput(
        risk_free_rate=0.07,  # 7.0%
        equity_risk_premium=0.055,  # 5.5%
        beta=1.2,
    )
    re = engine.calculate_cost_of_equity(capm_in)
    assert re == 0.136


def test_hamada_beta_unlever_and_relever():
    engine = CapitalCostEngine()

    # Raw levered beta = 1.2, D/E = 0.5, Tax = 25%
    # Beta_U = 1.2 / (1 + (1 - 0.25) * 0.5) = 1.2 / 1.375 = 0.8727
    beta_in = BetaAdjustmentInput(
        levered_beta=1.2,
        debt_to_equity_ratio=0.5,
        tax_rate=0.25,
    )
    unlevered = engine.unlever_beta(beta_in)
    assert unlevered == 0.8727

    # Relever back to target D/E = 0.8
    # Beta_L = 0.8727 * (1 + (1 - 0.25) * 0.8) = 0.8727 * 1.6 = 1.3963
    relevered = engine.relever_beta(
        unlevered_beta=unlevered,
        debt_to_equity_ratio=0.8,
        tax_rate=0.25,
    )
    assert relevered == 1.3963


def test_wacc_calculation():
    engine = CapitalCostEngine()
    wacc_in = WACCInput(
        symbol="TCS.NS",
        market_cap=800.0,
        total_debt=200.0,  # Total V = 1000.0 (E/V = 0.8, D/V = 0.2)
        cost_of_equity=0.12,  # 12%
        cost_of_debt=0.08,  # 8%
        tax_rate=0.25,  # 25% (After tax Rd = 6%)
    )
    res = engine.calculate_wacc(wacc_in)

    assert res.wacc == 0.108
    assert res.equity_weight == 0.8
    assert res.debt_weight == 0.2
    assert res.cost_of_debt_after_tax == 0.06
