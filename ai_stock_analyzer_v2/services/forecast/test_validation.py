"""
==========================================================
VALIDATION ENGINE UNIT TESTS
Module  : tests.forecast.test_validation
Layer   : Tests / Forecast / Validation
==========================================================
"""

import math

import pytest

from services.forecast.exceptions import ValuationError
from services.forecast.forecast_input import (
    ForecastInput,
    HistoricalDataPayload,
    ScenarioOverrideSpec,
)
from services.forecast.forecast_models import ForecastMethod
from services.forecast.validation import (
    validate_finite_series,
    validate_forecast_input,
    validate_non_negative_series,
)


def test_validate_finite_series_success():
    series = [100.0, 120.0, 150.0]
    validate_finite_series(series, "test_series")  # No error raised


def test_validate_finite_series_nan_raises():
    series = [100.0, math.nan, 120.0]
    with pytest.raises(ValuationError, match="Non-finite value"):
        validate_finite_series(series, "test_series")


def test_validate_finite_series_inf_raises():
    series = [100.0, math.inf, 120.0]
    with pytest.raises(ValuationError, match="Non-finite value"):
        validate_finite_series(series, "test_series")


def test_validate_non_negative_series_raises():
    series = [100.0, -10.0, 120.0]
    with pytest.raises(ValuationError, match="Negative value"):
        validate_non_negative_series(series, "test_series")


def test_validate_forecast_input_success():
    hist = HistoricalDataPayload(revenue=(100.0, 120.0, 150.0), capex=(10.0, 12.0, 15.0))
    inp = ForecastInput(
        ticker="TCS",
        historical_data=hist,
        forecast_horizon=3,
        primary_method=ForecastMethod.CAGR,
    )
    validate_forecast_input(inp)  # Passes cleanly


def test_validate_forecast_input_mismatched_override_length():
    hist = HistoricalDataPayload(revenue=(100.0, 120.0, 150.0))
    overrides = ScenarioOverrideSpec(revenue_growth_override=(0.10, 0.08))  # 2 years override
    inp = ForecastInput(
        ticker="TCS",
        historical_data=hist,
        forecast_horizon=3,  # 3 years horizon mismatch
        scenario_overrides=overrides,
    )
    with pytest.raises(ValuationError, match="Revenue growth override length"):
        validate_forecast_input(inp)
