"""
==========================================================
EXAMPLE: BASIC FORECAST MODEL USAGE
Module  : examples.forecast.basic_forecast
==========================================================
"""

from __future__ import annotations

import logging

from services.forecast.forecast_models import (
    ForecastAssumption,
    ForecastMethod,
    RevenueForecastModel,
    ScenarioModel,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Initializing basic forecast domain model example...")

    # 1. Define an explicit financial assumption
    assumption = ForecastAssumption(
        name="CAGR Growth Assumption",
        value=0.10,
        description="Applied 3-year historical CAGR to project future revenue.",
        source="historical_data",
    )

    # 2. Construct RevenueForecastModel
    rev_forecast = RevenueForecastModel(
        projected_revenue=(1000.0, 1100.0, 1210.0),
        growth_rates=(0.10, 0.10),
        method=ForecastMethod.CAGR,
        assumptions=(assumption,),
        historical=(800.0, 900.0),
    )
    logger.info("Created RevenueForecastModel: %s", rev_forecast)

    # 3. Construct ScenarioModel
    scenario = ScenarioModel(
        scenario_name="Base Case",
        probability=0.60,
        revenue_multiplier=1.0,
        margin_expansion_bps=0.0,
    )
    logger.info("Created ScenarioModel: %s", scenario)


if __name__ == "__main__":
    main()
