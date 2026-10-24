from __future__ import annotations

from decimal import Decimal

from domain.forecast.algorithms.cagr import CAGRCalculator
from domain.forecast.models import ForecastAssumption, ForecastMethod, ForecastResult


class ForecastApplicationService:
    """Application service orchestrating forecast workflows."""

    def execute_forecast(
        self, historical_values: tuple[Decimal, ...], assumption: ForecastAssumption
    ) -> ForecastResult:
        if assumption.method == ForecastMethod.CAGR:
            projected = CAGRCalculator.calculate(historical_values, assumption.periods)
            return ForecastResult(
                historical_values=historical_values,
                projected_values=projected,
                method=ForecastMethod.CAGR,
            )
        else:
            raise NotImplementedError(f"Forecast method {assumption.method} is not yet supported.")
