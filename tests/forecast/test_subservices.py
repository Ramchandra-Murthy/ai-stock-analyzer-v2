"""
==========================================================
EQUITY VALUATION PLATFORM v5.1
Module  : tests.forecast.test_subservices
==========================================================
"""

import pytest

from services.forecast.capex_forecast import CapExForecastEngine
from services.forecast.depreciation_forecast import DepreciationForecastEngine
from services.forecast.forecast_input import ForecastInput
from services.forecast.forecast_models import ForecastMethod
from services.forecast.tax_forecast import TaxForecastEngine
from services.forecast.working_capital_forecast import WorkingCapitalForecastEngine


@pytest.fixture
def base_input() -> ForecastInput:
    return ForecastInput(
        symbol="TCS.NS",
        historical_revenues=(100.0, 110.0, 120.0),
        forecast_years=2,
        historical_ebits=(20.0, 22.0, 24.0),
        historical_capex=(5.0, 5.5, 6.0),
        historical_depreciation=(2.0, 2.2, 2.4),
        historical_nwc=(10.0, 11.0, 12.0),
        method=ForecastMethod.CAGR,
    )


def test_capex_and_depreciation_engines(base_input: ForecastInput):
    capex_engine = CapExForecastEngine()
    dep_engine = DepreciationForecastEngine()

    projected_revs = (130.0, 140.0)

    capex_res = capex_engine.forecast_capex(base_input, projected_revs)
    dep_res = dep_engine.forecast_depreciation(base_input, projected_revs)

    assert len(capex_res.projected) == 2
    assert len(dep_res.projected) == 2


def test_working_capital_delta_calculation(base_input: ForecastInput):
    nwc_engine = WorkingCapitalForecastEngine()
    projected_revs = (130.0, 140.0)

    res = nwc_engine.forecast_working_capital(base_input, projected_revenues=projected_revs)
    assert len(res.projected_nwc) == 2


def test_tax_forecast_engine(base_input: ForecastInput) -> None:
    tax_engine = TaxForecastEngine()
    res = tax_engine.forecast_tax(base_input)
    assert res is not None
    assert len(res.projected) == base_input.forecast_years
