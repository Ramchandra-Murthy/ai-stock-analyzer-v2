from __future__ import annotations

import pytest

from services.forecast.exceptions import ForecastValidationError
from services.forecast.input import ForecastInput
from services.forecast.validation import ForecastValidator


@pytest.fixture
def valid_forecast_input() -> ForecastInput:
    return ForecastInput(
        ticker="INFY",
        historical_years=(2023, 2024, 2025),
        historical_revenue=(100.0, 110.0, 121.0),
        historical_margins=(0.20, 0.22, 0.25),
        historical_capex=(8.0, 9.0, 10.0),
        historical_depreciation=(4.0, 4.5, 5.0),
        historical_working_capital=(15.0, 16.0, 18.0),
        historical_taxes=(0.25, 0.25, 0.25),
        forecast_years=(2026, 2027),
    )


def test_validator_passes_valid_input(valid_forecast_input: ForecastInput) -> None:
    # Should not raise any exception
    ForecastValidator.validate_input(valid_forecast_input)


def test_validator_fails_empty_ticker(valid_forecast_input: ForecastInput) -> None:
    bad_input = ForecastInput(
        ticker="",
        historical_years=valid_forecast_input.historical_years,
        historical_revenue=valid_forecast_input.historical_revenue,
        historical_margins=valid_forecast_input.historical_margins,
        historical_capex=valid_forecast_input.historical_capex,
        historical_depreciation=valid_forecast_input.historical_depreciation,
        historical_working_capital=valid_forecast_input.historical_working_capital,
        historical_taxes=valid_forecast_input.historical_taxes,
        forecast_years=valid_forecast_input.forecast_years,
    )
    with pytest.raises(ForecastValidationError):
        ForecastValidator.validate_input(bad_input)


def test_validator_fails_length_mismatch(valid_forecast_input: ForecastInput) -> None:
    bad_input = ForecastInput(
        ticker=valid_forecast_input.ticker,
        historical_years=valid_forecast_input.historical_years,
        historical_revenue=(100.0, 110.0),  # Mismatch: 2 items for 3 years
        historical_margins=valid_forecast_input.historical_margins,
        historical_capex=valid_forecast_input.historical_capex,
        historical_depreciation=valid_forecast_input.historical_depreciation,
        historical_working_capital=valid_forecast_input.historical_working_capital,
        historical_taxes=valid_forecast_input.historical_taxes,
        forecast_years=valid_forecast_input.forecast_years,
    )
    with pytest.raises(ForecastValidationError):
        ForecastValidator.validate_input(bad_input)
