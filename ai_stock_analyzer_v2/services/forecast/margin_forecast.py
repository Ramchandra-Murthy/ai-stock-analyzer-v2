"""
==========================================================
EQUITY VALUATION PLATFORM v5.1
Module  : services.forecast.margin_forecast
Layer   : Services / Forecast / Subservices
Summary : Operating Margin (EBIT) Forecast Subservice executing
          historical mean and mean-reversion decay.
==========================================================
"""

from __future__ import annotations

from typing import Any

from core.logger import logger
from services.forecast.algorithms.mean_reversion import MeanReversionAlgorithm
from services.forecast.forecast_input import ForecastInput
from services.forecast.forecast_models import (
    AlgorithmInput,
    ConfidenceLevel,
    ForecastMethod,
    MarginForecast,
)


class MarginForecastEngine:
    """Subservice orchestrator for operating margin projections."""

    def __init__(self) -> None:
        self._mean_reversion_algo = MeanReversionAlgorithm()

    def forecast_margins(
        self,
        inp: ForecastInput,
        method: ForecastMethod | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> MarginForecast:
        """Calculates future EBIT margins based on historical ratio history."""
        symbol = inp.symbol
        logger.info(f"[MARGIN FORECAST] Projecting operating margins for {symbol}")

        # Compute historical EBIT margins
        if inp.historical_ebits is not None:
            historical_margins = tuple(
                ebit / rev if rev != 0 else 0.0
                for ebit, rev in zip(inp.historical_ebits, inp.historical_revenues, strict=False)
            )
        else:
            historical_margins = (0.15,) * len(inp.historical_revenues)

        mean_margin = (
            sum(historical_margins) / len(historical_margins) if historical_margins else 0.15
        )

        selected_method = method or inp.method

        if (
            selected_method == ForecastMethod.LINEAR_REGRESSION
            or selected_method == ForecastMethod.ROLLING_AVERAGE
            or selected_method == ForecastMethod.MEAN_REVERSION
        ):
            algo_input = AlgorithmInput(
                historical_values=historical_margins,
                forecast_periods=inp.forecast_years,
            )
            res = self._mean_reversion_algo.project_series(algo_input)
            projected = tuple(res.projected_values)
            method_used = ForecastMethod.MEAN_REVERSION
        else:
            projected = (round(mean_margin, 4),) * inp.forecast_years
            method_used = ForecastMethod.HISTORICAL_MEAN

        return MarginForecast(
            historical=historical_margins,
            projected=projected,
            method=method_used,
            confidence=ConfidenceLevel.MEDIUM,
            historical_mean_margin=round(mean_margin, 4),
        )
