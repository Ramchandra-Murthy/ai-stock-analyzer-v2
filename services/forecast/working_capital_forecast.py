"""
==========================================================
FORECAST ENGINE - WORKING CAPITAL FORECAST SERVICE
Module  : services.forecast.working_capital_forecast
Version : 5.1.0
Layer   : Services / Forecast
==========================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.logger import logger
from services.forecast.forecast_input import ForecastInput
from services.forecast.forecast_models import ForecastMethod


@dataclass(slots=True, frozen=True)
class WorkingCapitalForecast:
    """Working capital forecast structure."""

    projected_nwc: list[float]
    delta_nwc: list[float]
    method_used: str


class WorkingCapitalForecastEngine:
    """Computes Net Working Capital and Change in NWC."""

    def forecast_working_capital(
        self,
        inp_or_revs: Any,
        projected_revenues: list[float] | None = None,
        method: ForecastMethod = ForecastMethod.CAGR,
        *args: Any,
        **kwargs: Any,
    ) -> WorkingCapitalForecast:
        """Projects Net Working Capital requirement."""
        logger.info("[WORKING CAPITAL FORECAST] Projecting NWC requirements")

        if isinstance(inp_or_revs, ForecastInput):
            inp = inp_or_revs
            revs = projected_revenues if projected_revenues is not None else inp.historical_revenues
            nwc_hist = inp.historical_nwc
            forecast_years = inp.forecast_years
        else:
            revs = inp_or_revs if isinstance(inp_or_revs, list) else []
            nwc_hist = []
            forecast_years = len(revs) if revs else 5

        if nwc_hist and len(nwc_hist) > 0 and len(revs) >= len(nwc_hist):
            avg_ratio = sum(
                n / r if r > 0 else 0.10 for n, r in zip(nwc_hist, revs, strict=False)
            ) / len(nwc_hist)
        else:
            avg_ratio = 0.10

        projected = [round(r * avg_ratio, 4) for r in revs] if revs else [15.0] * forecast_years

        # Calculate year-over-year Change in NWC
        last_nwc = nwc_hist[-1] if nwc_hist else (projected[0] if projected else 10.0)
        delta_nwc = []
        for val in projected:
            delta_nwc.append(round(val - last_nwc, 4))
            last_nwc = val

        method_str = getattr(method, "value", str(method)).lower()

        return WorkingCapitalForecast(
            projected_nwc=projected,
            delta_nwc=delta_nwc,
            method_used=method_str,
        )

    forecast_nwc = forecast_working_capital


WorkingCapitalForecastService = WorkingCapitalForecastEngine
