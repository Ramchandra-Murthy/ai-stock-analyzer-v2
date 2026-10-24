"""
==========================================================
EXECUTABLE EXAMPLE - FORECAST ENGINE SUBSYSTEM
File    : examples/forecast/basic_forecast_example.py
Summary : Demonstrates construction of ForecastInput, creation of
          mock forecast projections, and usage of ForecastResult.
==========================================================
"""

from services.forecast.forecast_input import ForecastInput
from services.forecast.forecast_models import (
    CapexForecast,
    DepreciationForecast,
    ForecastConfidence,
    ForecastMethod,
    MarginForecast,
    RevenueForecast,
    TaxForecast,
    TerminalGrowthForecast,
    WorkingCapitalForecast,
)
from services.forecast.forecast_result import ForecastResult


def main() -> None:
    # 1. Instantiate Immutable Forecast Input
    inp = ForecastInput(
        symbol="RELIANCE.NS",
        historical_revenues=(1000.0, 1100.0, 1210.0),
        forecast_years=3,
        historical_ebits=(200.0, 220.0, 242.0),
        historical_capex=(50.0, 55.0, 60.5),
        historical_depreciation=(20.0, 22.0, 24.2),
        historical_nwc=(100.0, 110.0, 121.0),
        method=ForecastMethod.CAGR,
    )

    print(f"--- Forecasting Input Created for {inp.symbol} ---")
    print(f"Historical Revenue Series: {inp.historical_revenues}")
    print(f"Projection Horizon       : {inp.forecast_years} Years\n")

    # 2. Build Component Forecast Models
    rev = RevenueForecast(
        historical=inp.historical_revenues,
        projected=(1331.0, 1464.1, 1610.51),
        growth_rates=(0.10, 0.10, 0.10),
        method=ForecastMethod.CAGR,
    )
    margin = MarginForecast(
        historical=(0.20, 0.20, 0.20),
        projected=(0.20, 0.20, 0.20),
        method=ForecastMethod.HISTORICAL_MEAN,
    )
    capex = CapexForecast(
        historical=(50.0, 55.0, 60.5),
        projected=(66.55, 73.205, 80.5255),
        method=ForecastMethod.CAGR,
    )
    dep = DepreciationForecast(
        historical=(20.0, 22.0, 24.2),
        projected=(26.62, 29.282, 32.2102),
        method=ForecastMethod.CAGR,
    )
    nwc = WorkingCapitalForecast(
        historical=(100.0, 110.0, 121.0),
        projected=(133.1, 146.41, 161.051),
        delta=(12.1, 13.31, 14.641),
        method=ForecastMethod.CAGR,
    )
    tax = TaxForecast(
        historical=(50.0, 55.0, 60.5),
        projected=(66.55, 73.205, 80.5255),  # 25% Effective Tax Rate
        method=ForecastMethod.MANUAL,
    )
    term = TerminalGrowthForecast(
        terminal_growth=0.03,
        method=ForecastMethod.MANUAL,
    )
    confidence = ForecastConfidence(
        overall_score=92.0,
        revenue_score=95.0,
        margin_score=90.0,
        capex_score=90.0,
        tax_score=93.0,
    )

    # 3. Assemble Master Forecast Result
    result = ForecastResult(
        symbol=inp.symbol,
        revenue=rev,
        margin=margin,
        capex=capex,
        depreciation=dep,
        working_capital=nwc,
        tax=tax,
        terminal_growth=term,
        confidence=confidence,
    )

    # 4. Extract Derived FCFF Output
    print("--- Output Forecast Result Summary ---")
    print(f"Projected EBIT : {result.projected_ebit}")
    print(f"Projected NOPAT: {result.projected_nopat}")
    print(f"Projected FCFF : {result.projected_fcff}")


if __name__ == "__main__":
    main()
