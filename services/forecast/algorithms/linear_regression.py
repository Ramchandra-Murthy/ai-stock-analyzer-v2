from __future__ import annotations

from services.forecast.algorithms.base import BaseForecastAlgorithm
from services.forecast.exceptions import ForecastAlgorithmError
from services.forecast.input import ForecastInput


class LinearRegressionForecastAlgorithm(BaseForecastAlgorithm):
    def calculate(self, historical: tuple[float, ...], periods: int) -> tuple[float, ...]:
        """Project a historical series using linear regression (legacy API)."""
        values = tuple(float(value) for value in historical)
        if periods < 0:
            raise ValueError("periods must be non-negative")
        if periods == 0 or not values:
            return ()
        if len(values) == 1:
            return tuple(values[0] for _ in range(periods))
        n = len(values)
        mean_x = (n - 1) / 2.0
        mean_y = sum(values) / n
        numerator = sum((i - mean_x) * (value - mean_y) for i, value in enumerate(values))
        denominator = sum((i - mean_x) ** 2 for i in range(n))
        slope = numerator / denominator if denominator else 0.0
        intercept = mean_y - slope * mean_x
        return tuple(max(0.0, intercept + slope * (n - 1 + step)) for step in range(1, periods + 1))

    def calculate_revenue(self, forecast_input: ForecastInput) -> tuple[float, ...]:
        revenues = forecast_input.historical_revenue
        n = len(revenues)
        if n < 2:
            raise ForecastAlgorithmError("At least two points required.")
        x, y = list(range(n)), list(revenues)
        mean_x, mean_y = sum(x) / n, sum(y) / n
        numer = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denom = sum((x[i] - mean_x) ** 2 for i in range(n))
        slope = (numer / denom) if denom != 0 else 0.0
        intercept = mean_y - slope * mean_x
        projected = []
        for step in range(1, len(forecast_input.forecast_years) + 1):
            projected.append(max(0.0, intercept + slope * (n - 1 + step)))
        return tuple(projected)

    def calculate_margins(self, forecast_input: ForecastInput) -> tuple[float, ...]:
        margins = forecast_input.historical_margins
        avg = (sum(margins) / len(margins)) if margins else 0.0
        return tuple(max(0.0, min(1.0, avg)) for _ in forecast_input.forecast_years)

    def calculate_capex(self, forecast_input: ForecastInput) -> tuple[float, ...]:
        capex = forecast_input.historical_capex
        avg = (sum(capex) / len(capex)) if capex else 0.0
        return tuple(max(0.0, avg) for _ in forecast_input.forecast_years)

    def calculate_depreciation(self, forecast_input: ForecastInput) -> tuple[float, ...]:
        dep = forecast_input.historical_depreciation
        avg = (sum(dep) / len(dep)) if dep else 0.0
        return tuple(max(0.0, avg) for _ in forecast_input.forecast_years)

    def calculate_working_capital(self, forecast_input: ForecastInput) -> tuple[float, ...]:
        wc = forecast_input.historical_working_capital
        avg = (sum(wc) / len(wc)) if wc else 0.0
        return tuple(avg for _ in forecast_input.forecast_years)

    def calculate_taxes(self, forecast_input: ForecastInput) -> tuple[float, ...]:
        taxes = forecast_input.historical_taxes
        avg = (sum(taxes) / len(taxes)) if taxes else 0.25
        return tuple(max(0.0, min(1.0, avg)) for _ in forecast_input.forecast_years)


# Backward-compatible name used by the original forecast test suite.
LinearRegressionForecastEngine = LinearRegressionForecastAlgorithm
