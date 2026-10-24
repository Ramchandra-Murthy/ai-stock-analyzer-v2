"""
==========================================================
INPUT DOMAIN MODEL UNIT TESTS
Module  : tests.forecast.test_forecast_input
Layer   : Tests / Forecast / Input Models
==========================================================
"""

import pytest

from services.forecast.exceptions import ValuationError
from services.forecast.forecast_input import (
    ForecastInput,
    HistoricalDataPayload,
    ScenarioOverrideSpec,
)
from services.forecast.forecast_models import ForecastMethod


def test_historical_payload_valid():
    payload = HistoricalDataPayload(revenue=(100.0, 120.0, 140.0))
    assert payload.revenue == (100.0, 120.0, 140.0)


def test_historical_payload_insufficient_data():
    with pytest.raises(ValuationError, match="must contain at least 2 data points"):
        HistoricalDataPayload(revenue=(100.0,))


def test_forecast_input_valid_construction():
    hist = HistoricalDataPayload(revenue=(100.0, 120.0, 140.0))
    inp = ForecastInput(
        ticker="RELIANCE",
        historical_data=hist,
        forecast_horizon=5,
        primary_method=ForecastMethod.CAGR,
    )
    assert inp.ticker == "RELIANCE"
    assert inp.forecast_horizon == 5


def test_forecast_input_invalid_parameters():
    hist = HistoricalDataPayload(revenue=(100.0, 120.0))

    with pytest.raises(ValuationError, match="ticker must be a non-empty string"):
        ForecastInput(ticker="", historical_data=hist)

    with pytest.raises(ValuationError, match="forecast_horizon must be a positive integer"):
        ForecastInput(ticker="RELIANCE", historical_data=hist, forecast_horizon=0)

    with pytest.raises(ValuationError, match="terminal_growth_rate must be between"):
        ForecastInput(ticker="RELIANCE", historical_data=hist, terminal_growth_rate=0.15)

    with pytest.raises(ValuationError, match="discount_rate must be between"):
        ForecastInput(ticker="RELIANCE", historical_data=hist, discount_rate=-0.05)


def test_scenario_override_spec_optional_fields():
    spec = ScenarioOverrideSpec(capex_pct_revenue_override=0.08)
    assert spec.capex_pct_revenue_override == 0.08
    assert spec.revenue_growth_override is None
