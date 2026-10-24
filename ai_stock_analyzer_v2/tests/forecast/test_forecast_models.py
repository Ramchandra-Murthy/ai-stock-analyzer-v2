"""
==========================================================
UNIT TESTS: FORECAST DOMAIN MODELS
Module  : tests.forecast.test_forecast_models
==========================================================
"""

from __future__ import annotations

import pytest

from services.forecast.exceptions import ForecastValidationError
from services.forecast.models import (
    CapexForecast,
    ConfidenceLevel,
    DepreciationForecast,
    ForecastAssumption,
    ForecastConfidence,
    ForecastMethod,
    ForecastScenario,
    MarginForecast,
    RevenueForecast,
    TaxForecast,
    TerminalGrowthForecast,
    WorkingCapitalForecast,
)


def test_forecast_method_enum() -> None:
    assert ForecastMethod.CAGR.value == "CAGR"
    assert ForecastMethod.LINEAR_REGRESSION.value == "LINEAR_REGRESSION"


def test_confidence_level_enum() -> None:
    assert ConfidenceLevel.HIGH.value == "HIGH"
    assert ConfidenceLevel.LOW.value == "LOW"


def test_revenue_forecast_immutability_and_serialization() -> None:
    rev = RevenueForecast(values=(100.0, 110.0, 121.0), years=(2024, 2025, 2026))

    # Immutability check
    with pytest.raises(AttributeError):
        rev.values = (200.0,)  # type: ignore

    # Serialization round-trip
    d = rev.to_dict()
    rev_restored = RevenueForecast.from_dict(d)
    assert rev == rev_restored


def test_margin_forecast_validation() -> None:
    # Valid margin
    margin = MarginForecast(values=(0.15, 0.18), years=(2024, 2025))
    assert margin.values == (0.15, 0.18)

    # Invalid margin (> 1.0)
    with pytest.raises(ForecastValidationError):
        MarginForecast(values=(1.10,), years=(2024,))


def test_forecast_scenario_roundtrip() -> None:
    scenario = ForecastScenario(
        scenario_name="Base Case",
        method=ForecastMethod.CAGR,
        revenue=RevenueForecast(values=(1000.0,), years=(2024,)),
        margins=MarginForecast(values=(0.20,), years=(2024,)),
        capex=CapexForecast(values=(50.0,), years=(2024,)),
        depreciation=DepreciationForecast(values=(30.0,), years=(2024,)),
        working_capital=WorkingCapitalForecast(values=(100.0,), years=(2024,)),
        taxes=TaxForecast(values=(0.25,), years=(2024,)),
        terminal_growth=TerminalGrowthForecast(rate=0.03, confidence=ConfidenceLevel.HIGH),
        confidence=ForecastConfidence(score=85.0, level=ConfidenceLevel.HIGH),
        assumptions=ForecastAssumption(
            revenue_growth_rate=0.10,
            ebitda_margin=0.20,
            tax_rate=0.25,
            capex_pct_revenue=0.05,
            working_capital_pct_revenue=0.10,
        ),
    )

    serialized = scenario.to_dict()
    deserialized = ForecastScenario.from_dict(serialized)
    assert scenario == deserialized
