"""
==========================================================
TEST ASSUMPTION & CONFIDENCE ENGINES
Module  : tests.forecast.test_assumption_engine
==========================================================
"""

from __future__ import annotations

from services.forecast.assumption_engine import AssumptionEngine
from services.forecast.confidence_engine import ConfidenceEngine
from services.forecast.models import ConfidenceLevel, ForecastMethod


def test_assumption_engine_derivation() -> None:
    revenue = (1000.0, 1100.0, 1210.0)
    margins = (0.15, 0.16, 0.165)
    capex = (50.0, 55.0, 60.0)

    assumption = AssumptionEngine.derive_assumptions(
        historical_revenue=revenue,
        historical_margins=margins,
        historical_capex=capex,
        method=ForecastMethod.CAGR,
    )

    assert assumption.revenue_growth_rate > 0.0
    assert assumption.ebitda_margin == 0.165
    assert assumption.tax_rate == 0.25
    assert "engine" in assumption.metadata


def test_confidence_engine_evaluation() -> None:
    data = (100.0, 105.0, 110.0, 115.0)
    confidence = ConfidenceEngine.evaluate_confidence(data)
    assert confidence in list(ConfidenceLevel)
