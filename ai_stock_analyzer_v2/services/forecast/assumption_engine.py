"""Forecast assumption engine and legacy management-guidance compatibility."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from services.forecast.models import ForecastAssumption, ForecastMethod

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ManagementGuidance:
    """Optional management overrides used by the legacy forecast API."""

    revenue_cagr_override: float | None = None
    target_ebit_margin_override: float | None = None


class AssumptionEngine:
    """Engine for deriving and applying forward-looking assumptions."""

    @staticmethod
    def derive_assumptions(
        historical_revenue: tuple[float, ...],
        historical_margins: tuple[float, ...],
        historical_capex: tuple[float, ...],
        method: ForecastMethod = ForecastMethod.CAGR,
        **kwargs: Any,
    ) -> ForecastAssumption:
        logger.info("Deriving baseline assumptions using method: %s", method.value)
        rev_growth = (
            0.08
            if len(historical_revenue) < 2 or historical_revenue[0] == 0
            else (historical_revenue[-1] / historical_revenue[0])
            ** (1.0 / (len(historical_revenue) - 1))
            - 1.0
        )
        ebitda_m = historical_margins[-1] if historical_margins else 0.15
        tax_r = 0.25
        capex_pct = (
            0.05
            if not historical_capex or not historical_revenue or historical_revenue[-1] == 0
            else abs(historical_capex[-1] / historical_revenue[-1])
        )
        return ForecastAssumption(
            revenue_growth_rate=rev_growth,
            ebitda_margin=ebitda_m,
            tax_rate=tax_r,
            capex_pct_revenue=capex_pct,
            working_capital_pct_revenue=0.10,
            metadata={"engine": "AssumptionEngine", "method": method.value},
        )

    @staticmethod
    def apply_overrides(
        base_revenues: tuple[float, ...] | list[float],
        base_margins: tuple[float, ...] | list[float],
        guidance: ManagementGuidance,
    ) -> tuple[tuple[float, ...], tuple[float, ...]]:
        revenues = [float(v) for v in base_revenues]
        margins = [float(v) for v in base_margins]
        if guidance.revenue_cagr_override is not None and revenues:
            growth = float(guidance.revenue_cagr_override)
            last = revenues[0]
            projected: list[float] = []
            for _ in revenues:
                projected.append(last)
                last *= 1.0 + growth
            revenues = projected
        if guidance.target_ebit_margin_override is not None:
            margins = [float(guidance.target_ebit_margin_override) for _ in margins]
        return tuple(revenues), tuple(margins)
