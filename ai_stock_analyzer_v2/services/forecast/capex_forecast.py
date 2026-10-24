"""
==========================================================
EQUITY VALUATION PLATFORM v5.1
Module  : services.forecast.capex_forecast
Layer   : Services / Forecast / Subservices
Summary : Capital Expenditure (CapEx) Forecast Subservice.
==========================================================
"""

from __future__ import annotations

from typing import Any

from core.logger import logger
from services.forecast.forecast_input import ForecastInput
from services.forecast.models import (
    CapexForecast,
    ConfidenceLevel,
    ForecastMethod,
)


class CapexForecastEngine:
    """Subservice orchestrator for capital expenditure projections."""

    def forecast_capex(
        self,
        inp: ForecastInput,
        projected_revenues: tuple[float, ...] | None = None,
        method: ForecastMethod | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> CapexForecast:
        """Projects future CapEx based on historical CapEx-to-Revenue ratio or CAGR."""
        # Handle positional parameter flexibility where method or revenues may be passed
        if isinstance(projected_revenues, (ForecastMethod, str)):
            method = projected_revenues  # type: ignore[assignment]
            projected_revenues = args[0] if args and isinstance(args[0], (tuple, list)) else None

        symbol = inp.symbol
        logger.info(f"[CAPEX FORECAST] Projecting CapEx for {symbol}")

        hist_capex = tuple(inp.historical_capex) if inp.historical_capex else ()
        hist_revs = tuple(inp.historical_revenues) if inp.historical_revenues else ()

        if hist_capex and hist_revs:
            ratios = tuple(
                cap / rev if rev != 0 else 0.05
                for cap, rev in zip(hist_capex, hist_revs, strict=False)
            )
            capex_ratio = sum(ratios) / len(ratios) if ratios else 0.05
        else:
            capex_ratio = 0.05

        if projected_revenues is not None:
            projected = tuple(round(rev * capex_ratio, 4) for rev in projected_revenues)
        else:
            last_capex = hist_capex[-1] if hist_capex else 10.0
            projected = (round(last_capex, 4),) * inp.forecast_years

        return CapexForecast(
            historical=hist_capex,
            projected=projected,
            method=(method if isinstance(method, ForecastMethod) else ForecastMethod.CAGR),
            confidence=ConfidenceLevel.MEDIUM,
        )


CapExForecastEngine = CapexForecastEngine
