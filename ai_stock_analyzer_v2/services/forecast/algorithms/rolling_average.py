"""
Module: services.forecast.algorithms.rolling_average
Description: Institutional rolling moving-average forecasting calculation engine.
Author: Engineering Team
Python Version: 3.13+
"""

from __future__ import annotations


class RollingAverageForecastEngine:
    """Pure mathematical engine for rolling window moving-average projections."""

    def calculate(
        self, historical: tuple[float, ...], periods: int, **kwargs: float
    ) -> tuple[float, ...]:
        """
        Projects future values using a rolling or windowed moving average of historical observations.

        Parameters:
            historical: Tuple of historical numerical observations.
            periods: Number of future periods to project.
            **kwargs: Optional parameters including 'window_size' (default uses all available history).

        Returns:
            Tuple of projected float values.
        """
        n = len(historical)
        if n == 0 or periods <= 0:
            return ()

        # Determine window size from kwargs, defaulting to full history length
        window_size = int(kwargs.get("window_size", n))
        window_size = max(1, min(window_size, n))

        # Extract the relevant tail window for average calculation
        window_data = historical[-window_size:]
        base_average = sum(window_data) / len(window_data)

        # Optional mean reversion pull or growth drift
        drift = kwargs.get("drift_rate", 0.0)

        projected = []
        current_val = base_average
        for _step in range(1, periods + 1):
            current_val *= 1.0 + drift
            projected.append(float(current_val))

        return tuple(projected)
