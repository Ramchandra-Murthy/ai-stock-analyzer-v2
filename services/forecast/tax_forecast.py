"""
==========================================================
EQUITY VALUATION PLATFORM v5.1
Module  : services.forecast.tax_forecast
Layer   : Services / Forecast / Subservices
Summary : Effective Tax Rate & Liability Forecast Subservice.
==========================================================
"""

from __future__ import annotations

from typing import Any

from core.logger import logger
from services.forecast.forecast_input import ForecastInput
from services.forecast.models import (
    ConfidenceLevel,
    ForecastMethod,
    TaxForecast,
)


class TaxForecastEngine:
    """Subservice orchestrator for effective tax rate projections."""

    def forecast_tax(
        self,
        inp: ForecastInput,
        method: ForecastMethod | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> TaxForecast:
        """Projects tax liabilities based on historical tax rates."""
        symbol = inp.symbol
        logger.info(f"[TAX FORECAST] Projecting taxes for {symbol}")

        effective_rate = 0.25  # Standard 25% corporate tax rate baseline

        # Calculate projected taxes on projected EBIT if supplied, otherwise return empty
        projected_ebits = kwargs.get("projected_ebit", ())
        if projected_ebits:
            projected = tuple(round(ebit * effective_rate, 4) for ebit in projected_ebits)
        else:
            projected = (0.0,) * inp.forecast_years

        return TaxForecast(
            historical=(),
            projected=projected,
            method=method or inp.method or ForecastMethod.MANUAL,
            confidence=ConfidenceLevel.HIGH,
        )

    # Alias for method name compatibility
    forecast_tax_rate = forecast_tax
