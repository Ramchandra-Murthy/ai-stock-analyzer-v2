"""
==========================================================
MEAN REVERSION FORECAST ALGORITHM MODULE
Module  : services.forecast.algorithms.mean_reversion
Layer   : Services / Forecast / Algorithms
==========================================================

Purpose
-------
Implements mean-reversion modeling to project values transitioning
gradually from recent baseline levels back toward long-term historical averages.
"""

from __future__ import annotations

from services.forecast.exceptions import ValuationError


class MeanReversionCalculator:
    """Calculates mean-reversion projections over a specified convergence horizon."""

    @staticmethod
    def project(
        historical_values: tuple[float, ...],
        horizon: int,
        reversion_speed: float = 0.5,
    ) -> tuple[float, ...]:
        """
        Projects future values converging from the most recent historical value
        toward the historical mean.

        reversion_speed determines the rate of convergence (0.0 = no movement from recent,
        1.0 = instant jump to historical mean in year 1).
        """
        if not historical_values or len(historical_values) < 2:
            raise ValuationError("At least 2 periods are required for mean reversion forecasting.")

        if horizon < 1:
            raise ValuationError("Forecast horizon must be at least 1 year.")

        if not (0.0 <= reversion_speed <= 1.0):
            raise ValuationError("Reversion speed must be between 0.0 and 1.0 inclusive.")

        historical_mean = sum(historical_values) / len(historical_values)
        last_val = historical_values[-1]

        projected = []
        current = last_val
        for step in range(1, horizon + 1):
            # Gradual pull toward historical mean weighted by step and reversion speed
            current = current + reversion_speed * (historical_mean - current) / step
            projected.append(float(current))

        return tuple(projected)
