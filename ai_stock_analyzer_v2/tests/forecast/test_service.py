"""
Module: tests.forecast.test_service
Description: Comprehensive unit tests for the ForecastService orchestrator.
Author: Engineering Team
Python Version: 3.13+
"""

from __future__ import annotations

from services.forecast.models import ConfidenceLevel, ForecastMethod
from services.forecast.service import ForecastService


def test_forecast_service_revenue() -> None:
    """Verify service correctly orchestrates revenue projections and growth rates."""
    service = ForecastService()
    historical = (100.0, 110.0, 121.0)

    rev_forecast = service.generate_revenue_forecast(
        historical=historical,
        periods=2,
        method=ForecastMethod.CAGR,
        confidence=ConfidenceLevel.HIGH,
    )

    assert rev_forecast.historical == historical
    assert len(rev_forecast.projected) == 2
    assert len(rev_forecast.growth_rates) == 2
    assert rev_forecast.method == ForecastMethod.CAGR
    assert rev_forecast.confidence == ConfidenceLevel.HIGH


def test_forecast_service_working_capital() -> None:
    """Verify service working capital delta calculations."""
    service = ForecastService()
    historical = (50.0, 60.0)

    wc_forecast = service.generate_working_capital_forecast(
        historical=historical,
        periods=2,
        method=ForecastMethod.LINEAR_REGRESSION,
    )

    assert len(wc_forecast.delta) == 2
    assert isinstance(wc_forecast.delta, tuple)


def test_forecast_service_scenario() -> None:
    """Verify end-to-end scenario bundling through the service layer."""
    service = ForecastService()

    scenario = service.generate_scenario(
        scenario_name="Base Case",
        probability=0.60,
        historical_revenue=(1000.0, 1100.0),
        historical_margin=(0.15, 0.16),
        historical_capex=(50.0, 55.0),
        periods=3,
        method=ForecastMethod.CAGR,
    )

    assert scenario.scenario_name == "Base Case"
    assert scenario.probability == 0.60
    assert scenario.revenue_forecast is not None
    assert scenario.margin_forecast is not None
    assert scenario.capex_forecast is not None
    assert scenario.tax_forecast is not None
    assert scenario.terminal_growth is not None

    # Test round-trip dictionary serialization on the full scenario
    serialized = scenario.to_dict()
    reconstructed = scenario.from_dict(serialized)
    assert scenario == reconstructed
