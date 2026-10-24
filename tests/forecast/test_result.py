"""
==========================================================
TEST FORECAST RESULT DOMAIN CONTRACTS
Module  : tests.forecast.test_result
Layer   : Tests / Forecast / Output DTOs
==========================================================
"""

from __future__ import annotations

from services.forecast.models import (
    ConfidenceLevel,
    ForecastMethod,
    MarginForecast,
    RevenueForecast,
)
from services.forecast.result import ForecastResult


def test_forecast_result_initialization_and_serialization() -> None:
    rev_forecast = RevenueForecast(
        historical=(100.0, 110.0),
        projected=(121.0, 133.1),
        method=ForecastMethod.CAGR,
        confidence=ConfidenceLevel.HIGH,
        growth_rates=(0.10, 0.10),
    )
    margin_forecast = MarginForecast(
        historical=(0.20, 0.22),
        projected=(0.22, 0.22),
        method=ForecastMethod.HISTORICAL_MEAN,
        confidence=ConfidenceLevel.MEDIUM,
    )

    result = ForecastResult(
        symbol="AAPL",
        forecast_horizon=2,
        method_used=ForecastMethod.CAGR,
        confidence_level=ConfidenceLevel.HIGH,
        confidence_score=0.85,
        revenue_forecast=rev_forecast,
        margin_forecast=margin_forecast,
        ebit_forecast=(26.62, 29.28),
        capex_forecast=(5.0, 5.5),
        metadata={"model_version": "5.1.0"},
    )

    assert result.symbol == "AAPL"
    assert result.forecast_horizon == 2
    assert result.confidence_score == 0.85
    assert result.ebit_forecast == (26.62, 29.28)

    # Test dictionary serialization
    serialized = result.to_dict()
    assert serialized["symbol"] == "AAPL"
    assert serialized["method_used"] == "cagr"
    assert serialized["confidence_level"] == "high"
    assert serialized["revenue_forecast"]["projected"] == [121.0, 133.1]
    assert serialized["metadata"]["model_version"] == "5.1.0"
