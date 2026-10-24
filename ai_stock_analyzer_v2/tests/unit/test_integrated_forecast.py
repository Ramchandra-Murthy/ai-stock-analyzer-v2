import pytest

from services.forecast.forecast_service import ForecastService


def test_forecast_service_integration():
    service = ForecastService()

    historical_revenues = [100000.0, 115000.0, 132000.0, 150000.0]
    historical_ebits = [15000.0, 17250.0, 19800.0, 22500.0]
    historical_nwc = [10000.0, 11500.0, 13200.0, 15000.0]
    historical_capex = [-5000.0, -5750.0, -6600.0, -7500.0]

    forecast = service.build_forecast(
        historical_revenues=historical_revenues,
        historical_ebits=historical_ebits,
        historical_nwc=historical_nwc,
        historical_capex=historical_capex,
        forecast_years=5,
    )

    assert len(forecast.projected_revenues) == 5
    assert len(forecast.projected_ebit_margins) == 5
    assert len(forecast.projected_nwc) == 5
    assert len(forecast.projected_capex) == 5
    assert forecast.projected_revenues[0] > historical_revenues[-1]
    assert forecast.projected_ebit_margins[0] == pytest.approx(0.15, abs=1e-3)
