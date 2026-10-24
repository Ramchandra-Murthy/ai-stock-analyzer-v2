from __future__ import annotations

import math

from services.forecast.exceptions import ForecastValidationError
from services.forecast.input import ForecastInput


class ForecastValidator:
    """Validates ForecastInput payloads for structural and numerical integrity."""

    @staticmethod
    def validate_input(forecast_input: ForecastInput) -> None:
        if not forecast_input.ticker or not forecast_input.ticker.strip():
            raise ForecastValidationError("Ticker symbol must be a non-empty string.")

        h_years = forecast_input.historical_years
        h_rev = forecast_input.historical_revenue
        h_margins = forecast_input.historical_margins
        h_capex = forecast_input.historical_capex
        h_dep = forecast_input.historical_depreciation
        h_wc = forecast_input.historical_working_capital
        h_tax = forecast_input.historical_taxes
        f_years = forecast_input.forecast_years

        if not h_years:
            raise ForecastValidationError("Historical years sequence cannot be empty.")

        n_years = len(h_years)
        series_map = {
            "historical_revenue": h_rev,
            "historical_margins": h_margins,
            "historical_capex": h_capex,
            "historical_depreciation": h_dep,
            "historical_working_capital": h_wc,
            "historical_taxes": h_tax,
        }

        for name, series in series_map.items():
            if len(series) != n_years:
                raise ForecastValidationError(
                    f"Length mismatch: {name} length ({len(series)}) must match historical_years length ({n_years})."
                )
            for val in series:
                if math.isnan(val) or math.isinf(val):
                    raise ForecastValidationError(
                        f"Invalid numeric value (NaN or Inf) found in {name}: {val}"
                    )

        if not f_years:
            raise ForecastValidationError("Forecast years sequence cannot be empty.")

        for val in h_rev:
            if val <= 0.0:
                raise ForecastValidationError(
                    f"Historical revenue must be strictly positive, found: {val}"
                )

        for name, series in [
            ("historical_margins", h_margins),
            ("historical_taxes", h_tax),
        ]:
            for val in series:
                if not (0.0 <= val <= 1.0):
                    raise ForecastValidationError(
                        f"Value in {name} must be between 0.0 and 1.0, found: {val}"
                    )

        if forecast_input.custom_growth_rate is not None:
            if math.isnan(forecast_input.custom_growth_rate) or math.isinf(
                forecast_input.custom_growth_rate
            ):
                raise ForecastValidationError("Custom growth rate must be a finite number.")
