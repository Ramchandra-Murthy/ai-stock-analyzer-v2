import pytest

from core.exceptions import ValuationError
from services.capital.capital_models import CapitalStructure
from services.capital.wacc_service import WACCService


def test_wacc_calculation_flow():
    wacc_service = WACCService()
    cap_struct = CapitalStructure(
        market_cap=800000.0, total_debt=200000.0, cash_and_equivalents=50000.0
    )

    result = wacc_service.compute_wacc(
        risk_free_rate=0.07,  # 7.0% India G-Sec
        beta=1.10,  # Beta
        equity_risk_premium=0.06,  # 6.0% ERP
        pre_tax_cost_of_debt=0.085,  # 8.5% Cost of Debt
        tax_rate=0.25,  # 25% Effective Tax Rate
        capital_structure=cap_struct,
    )

    assert result.cost_of_equity == pytest.approx(0.136, abs=1e-3)
    assert result.cost_of_debt_post_tax == pytest.approx(0.06375, abs=1e-4)
    assert result.weight_equity == pytest.approx(0.80, abs=1e-2)
    assert result.weight_debt == pytest.approx(0.20, abs=1e-2)
    assert result.wacc == pytest.approx(0.12155, abs=1e-3)


def test_wacc_invalid_inputs():
    wacc_service = WACCService()
    cap_struct = CapitalStructure(market_cap=100.0, total_debt=50.0, cash_and_equivalents=10.0)

    with pytest.raises(ValuationError):
        wacc_service.compute_wacc(
            risk_free_rate=-0.01,  # Invalid negative Rf
            beta=1.0,
            equity_risk_premium=0.05,
            pre_tax_cost_of_debt=0.08,
            tax_rate=0.25,
            capital_structure=cap_struct,
        )
