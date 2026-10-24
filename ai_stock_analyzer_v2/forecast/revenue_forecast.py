from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ForecastError
from core.logger import logger


@dataclass(slots=True, frozen=True)
class RevenueForecastOutput:
    historical_cagr: float
    projected_growth_rates: list[float]
    base_revenue: float
    projected_revenues: list[float]


class RevenueForecastEngine:
    @staticmethod
    def project_revenue(
        historical_revenues: list[float],
        forecast_years: int = 5,
        decay_factor: float = 0.95,
        min_growth_cap: float = 0.02,
        max_growth_cap: float = 0.25,
    ) -> RevenueForecastOutput:
        if len(historical_revenues) < 2:
            raise ForecastError("At least 2 historical revenue periods are required.")

        base_revenue = historical_revenues[-1]
        n_periods = len(historical_revenues) - 1
        cagr = ((base_revenue / historical_revenues[0]) ** (1.0 / n_periods)) - 1.0
        initial_growth = max(min(cagr, max_growth_cap), min_growth_cap)

        projected_growth_rates: list[float] = []
        projected_revenues: list[float] = []
        current_rev = base_revenue
        current_growth = initial_growth

        for y in range(forecast_years):
            if y > 0:
                current_growth = max(current_growth * decay_factor, min_growth_cap)
            projected_growth_rates.append(round(current_growth, 4))
            current_rev *= 1.0 + current_growth
            projected_revenues.append(round(current_rev, 2))

        logger.info(f"[FORECAST] Historical CAGR: {cagr:.2%} | Growth: {projected_growth_rates}")

        return RevenueForecastOutput(
            historical_cagr=round(cagr, 4),
            projected_growth_rates=projected_growth_rates,
            base_revenue=base_revenue,
            projected_revenues=projected_revenues,
        )
