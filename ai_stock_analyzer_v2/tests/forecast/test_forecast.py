from __future__ import annotations

import pytest

from services.forecast.algorithms.cagr import CAGRForecastAlgorithm
from services.forecast.input import ForecastInput
from services.forecast.service import ForecastService
from services.forecast.validation import ForecastValidator


@pytest.fixture
def valid_input() -> ForecastInput:
    return ForecastInput(
        ticker="RELIANCE",
        historical_years=(2023, 2024, 2025),
        historical_revenue=(100.0, 110.0, 121.0),
        historical_margins=(0.10, 0.12, 0.15),
        historical_capex=(10.0, 11.0, 12.0),
        historical_depreciation=(5.0, 5.5, 6.0),
        historical_working_capital=(20.0, 22.0, 24.0),
        historical_taxes=(0.25, 0.25, 0.25),
        forecast_years=(2026, 2027),
    )


def test_validator_success(valid_input: ForecastInput) -> None:
    ForecastValidator.validate_input(valid_input)


def test_cagr_algorithm(valid_input: ForecastInput) -> None:
    algo = CAGRForecastAlgorithm()
    revenues = algo.calculate_revenue(valid_input)
    assert len(revenues) == 2
    assert pytest.approx(revenues[0], 0.01) == 133.1


def test_forecast_service_execution(valid_input: ForecastInput) -> None:
    service = ForecastService(algorithm=CAGRForecastAlgorithm())
    result = service.execute(valid_input)
    assert result.status == "SUCCESS"
    assert result.package.ticker == "RELIANCE"
