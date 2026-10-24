import pytest

from core.exceptions import ValidationError
from services.forecast.forecast_input import ForecastInput
from services.forecast.forecast_models import ScenarioType
from services.forecast.forecast_service import ForecastService


def test_epic1_forecast_engine_full_flow():
    service = ForecastService()

    inp = ForecastInput(
        symbol="TATASTEEL",
        historical_revenues=[100000.0, 115000.0, 132000.0, 150000.0],
        historical_ebits=[15000.0, 17250.0, 19800.0, 22500.0],
        historical_nwc=[10000.0, 11500.0, 13200.0, 15000.0],
        historical_capex=[5000.0, 5750.0, 6600.0, 7500.0],
        historical_depreciation=[3000.0, 3450.0, 3960.0, 4500.0],
        historical_pbt=[12000.0, 13800.0, 15840.0, 18000.0],
        historical_tax=[3000.0, 3450.0, 3960.0, 4500.0],
        forecast_years=5,
    )

    scenarios = service.generate_full_forecast(inp)

    assert ScenarioType.BASE in scenarios
    assert ScenarioType.BULL in scenarios
    assert ScenarioType.BEAR in scenarios

    base = scenarios[ScenarioType.BASE]
    assert len(base.yearly_forecasts) == 5
    assert base.symbol == "TATASTEEL"
    assert base.effective_tax_rate == pytest.approx(0.25, abs=1e-2)
    assert base.projected_fcfs[0] > 0.0

    bull = scenarios[ScenarioType.BULL]
    assert bull.projected_revenues[0] > base.projected_revenues[0]


def test_epic1_validation_failure():
    service = ForecastService()

    with pytest.raises(ValidationError):
        invalid_inp = ForecastInput(
            symbol="INVALID",
            historical_revenues=[100.0],  # Insufficient length (< 2)
            historical_ebits=[10.0],
            historical_nwc=[10.0],
            historical_capex=[5.0],
            historical_depreciation=[2.0],
        )
        service.generate_full_forecast(invalid_inp)
