"""
==========================================================
UNIT TESTS: FORECAST DOMAIN MODELS
Module  : services.forecast.tests.test_models
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
    ForecastFrequency,
    ForecastMetadata,
    ForecastMethod,
    ForecastPackage,
    ForecastScenario,
    MarginForecast,
    RevenueForecast,
    ScenarioType,
    TaxForecast,
    TerminalGrowthForecast,
    WorkingCapitalForecast,
)


def test_enums() -> None:
    assert ForecastMethod.CAGR.value == "CAGR"
    assert ConfidenceLevel.HIGH.value == "HIGH"
    assert ForecastFrequency.ANNUAL.value == "ANNUAL"
    assert ScenarioType.BASE.value == "BASE"


def test_forecast_series_validation() -> None:
    # Valid
    series = RevenueForecast(values=(100.0, 110.0), years=(2024, 2025))
    assert series.values == (100.0, 110.0)

    # Length mismatch
    with pytest.raises(ForecastValidationError):
        RevenueForecast(values=(100.0,), years=(2024, 2025))


def test_margin_and_tax_bounds() -> None:
    # Valid margins/taxes
    assert MarginForecast(values=(0.2,), years=(2024,)).values == (0.2,)
    assert TaxForecast(values=(0.25,), years=(2024,)).values == (0.25,)

    # Invalid margin (> 1.0)
    with pytest.raises(ForecastValidationError):
        MarginForecast(values=(1.05,), years=(2024,))

    # Invalid tax (< 0.0)
    with pytest.raises(ForecastValidationError):
        TaxForecast(values=(-0.01,), years=(2024,))


def test_terminal_growth_bounds() -> None:
    tg = TerminalGrowthForecast(rate=0.03, confidence=ConfidenceLevel.HIGH)
    assert tg.rate == 0.03

    with pytest.raises(ForecastValidationError):
        TerminalGrowthForecast(rate=0.15, confidence=ConfidenceLevel.HIGH)


def test_confidence_bounds() -> None:
    conf = ForecastConfidence(score=85.0, level=ConfidenceLevel.MEDIUM)
    assert conf.score == 85.0

    with pytest.raises(ForecastValidationError):
        ForecastConfidence(score=105.0, level=ConfidenceLevel.MEDIUM)


def test_forecast_package_round_trip() -> None:
    metadata = ForecastMetadata(
        created_at="2026-04-06", author="Quant Team", version="v5.1.0-alpha.1"
    )
    scenario = ForecastScenario(
        scenario_type=ScenarioType.BASE,
        method=ForecastMethod.CAGR,
        revenue=RevenueForecast(values=(1000.0, 1100.0), years=(2024, 2025)),
        margins=MarginForecast(values=(0.2, 0.22), years=(2024, 2025)),
        capex=CapexForecast(values=(50.0, 55.0), years=(2024, 2025)),
        depreciation=DepreciationForecast(values=(20.0, 22.0), years=(2024, 2025)),
        working_capital=WorkingCapitalForecast(values=(100.0, 110.0), years=(2024, 2025)),
        taxes=TaxForecast(values=(0.25, 0.25), years=(2024, 2025)),
        terminal_growth=TerminalGrowthForecast(rate=0.025, confidence=ConfidenceLevel.HIGH),
        confidence=ForecastConfidence(score=90.0, level=ConfidenceLevel.HIGH),
        assumptions=ForecastAssumption(
            revenue_growth_rate=0.10,
            ebitda_margin=0.20,
            tax_rate=0.25,
            capex_pct_revenue=0.05,
            working_capital_pct_revenue=0.10,
        ),
    )
    package = ForecastPackage(ticker="RELIANCE", scenarios=(scenario,), metadata=metadata)

    d = package.to_dict()
    restored = ForecastPackage.from_dict(d)
    assert package == restored
