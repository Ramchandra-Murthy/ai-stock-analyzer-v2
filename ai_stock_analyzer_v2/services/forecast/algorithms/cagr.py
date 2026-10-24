from __future__ import annotations

from services.forecast.algorithms.base import BaseForecastAlgorithm
from services.forecast.exceptions import ForecastAlgorithmError
from services.forecast.input import ForecastInput


class CAGRForecastAlgorithm(BaseForecastAlgorithm):
    def calculate(self, historical: tuple[float, ...], periods: int) -> tuple[float, ...]:
        """Project a historical series using CAGR (legacy API)."""
        values = tuple(float(value) for value in historical)
        if periods < 0:
            raise ValueError("periods must be non-negative")
        if periods == 0 or not values:
            return ()
        if len(values) == 1:
            return tuple(values[0] for _ in range(periods))
        if values[0] <= 0:
            # Legacy forecast contract: zero/negative starting history falls back to a flat projection.
            return tuple(values[-1] for _ in range(periods))
        rate = (values[-1] / values[0]) ** (1.0 / (len(values) - 1)) - 1.0
        projected = []
        last_value = values[-1]
        for _ in range(periods):
            last_value *= 1.0 + rate
            projected.append(last_value)
        return tuple(projected)

    def calculate_revenue(self, forecast_input: ForecastInput) -> tuple[float, ...]:
        revenues = forecast_input.historical_revenue
        if len(revenues) < 2:
            raise ForecastAlgorithmError("At least two historical revenue points are required.")
        start_val, end_val, n_periods = revenues[0], revenues[-1], len(revenues) - 1
        if start_val <= 0:
            raise ForecastAlgorithmError("Initial historical revenue must be strictly positive.")
        cagr = (end_val / start_val) ** (1.0 / n_periods) - 1.0
        if forecast_input.custom_growth_rate is not None:
            cagr = forecast_input.custom_growth_rate
        projected, last_val = [], end_val
        for _ in forecast_input.forecast_years:
            last_val *= 1.0 + cagr
            projected.append(last_val)
        return tuple(projected)

    def calculate_margins(self, forecast_input: ForecastInput) -> tuple[float, ...]:
        margins = forecast_input.historical_margins
        last_margin = margins[-1] if margins else 0.0
        return tuple(max(0.0, min(1.0, last_margin)) for _ in forecast_input.forecast_years)

    def calculate_capex(self, forecast_input: ForecastInput) -> tuple[float, ...]:
        capex = forecast_input.historical_capex
        last_capex = capex[-1] if capex else 0.0
        return tuple(max(0.0, last_capex) for _ in forecast_input.forecast_years)

    def calculate_depreciation(self, forecast_input: ForecastInput) -> tuple[float, ...]:
        dep = forecast_input.historical_depreciation
        last_dep = dep[-1] if dep else 0.0
        return tuple(max(0.0, last_dep) for _ in forecast_input.forecast_years)

    def calculate_working_capital(self, forecast_input: ForecastInput) -> tuple[float, ...]:
        wc = forecast_input.historical_working_capital
        last_wc = wc[-1] if wc else 0.0
        return tuple(last_wc for _ in forecast_input.forecast_years)

    def calculate_taxes(self, forecast_input: ForecastInput) -> tuple[float, ...]:
        taxes = forecast_input.historical_taxes
        last_tax = taxes[-1] if taxes else 0.25
        return tuple(max(0.0, min(1.0, last_tax)) for _ in forecast_input.forecast_years)


# Backward-compatible name used by the original forecast test suite.
CAGRForecastEngine = CAGRForecastAlgorithm
