from __future__ import annotations

import pytest

from capital.wacc_engine import CapitalCostEngine
from core.exceptions import ForecastError
from forecast.revenue_forecast import RevenueForecastEngine


def test_revenue_forecast_cagr():
    revenues = [100.0, 120.0, 144.0]  # 20% CAGR
    res = RevenueForecastEngine.project_revenue(revenues, forecast_years=5)
    assert res.historical_cagr == pytest.approx(0.20, abs=1e-2)
    assert len(res.projected_growth_rates) == 5


def test_revenue_forecast_insufficient_data():
    with pytest.raises(ForecastError):
        RevenueForecastEngine.project_revenue([100.0])


def test_capital_cost_wacc_calculation():
    cap = CapitalCostEngine.calculate_wacc(
        risk_free_rate=0.07,
        beta=1.0,
        equity_risk_premium=0.05,
        pre_tax_cost_of_debt=0.08,
        tax_rate=0.25,
        market_cap=800.0,
        total_debt=200.0,
    )
    # Ke = 7% + 5% = 12%
    # Kd = 8% * 0.75 = 6%
    # WACC = (0.8 * 12%) + (0.2 * 6%) = 9.6% + 1.2% = 10.8%
    assert cap.cost_of_equity == 0.12
    assert cap.cost_of_debt_post_tax == 0.06
    assert cap.wacc == pytest.approx(0.108, abs=1e-3)
