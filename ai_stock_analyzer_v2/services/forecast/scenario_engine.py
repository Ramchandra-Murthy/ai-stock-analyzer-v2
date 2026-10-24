from __future__ import annotations

from core.logger import logger
from services.forecast.forecast_models import ScenarioType
from services.forecast.forecast_result import ForecastResult, YearForecast


class ScenarioEngine:
    """Generates Bull, Base, and Bear scenario variants from a Base Forecast Result."""

    def build_scenarios(self, base_result: ForecastResult) -> dict[ScenarioType, ForecastResult]:
        logger.info(f"[SCENARIO ENGINE] Building Bull/Base/Bear scenarios for {base_result.symbol}")

        bull = self._apply_multiplier(
            base_result, ScenarioType.BULL, rev_mult=1.05, margin_mult=1.10
        )
        bear = self._apply_multiplier(
            base_result, ScenarioType.BEAR, rev_mult=0.92, margin_mult=0.85
        )

        return {
            ScenarioType.BASE: base_result,
            ScenarioType.BULL: bull,
            ScenarioType.BEAR: bear,
        }

    def _apply_multiplier(
        self,
        base: ForecastResult,
        scenario: ScenarioType,
        rev_mult: float,
        margin_mult: float,
    ) -> ForecastResult:
        adj_revs = [r * rev_mult for r in base.projected_revenues]
        adj_ebits = [e * margin_mult for e in base.projected_ebits]
        adj_nwc = [n * rev_mult for n in base.projected_nwc]
        adj_capex = [c * rev_mult for c in base.projected_capex]
        adj_dep = [d * rev_mult for d in base.projected_depreciation]
        adj_taxes = [t * margin_mult for t in base.projected_taxes]

        adj_fcfs = [
            ebit - tax + dep - capex - (nwc * 0.1)
            for ebit, tax, dep, capex, nwc in zip(
                adj_ebits, adj_taxes, adj_dep, adj_capex, adj_nwc, strict=False
            )
        ]

        yearly = [
            YearForecast(
                year=i + 1,
                revenue=adj_revs[i],
                ebit=adj_ebits[i],
                ebit_margin=(adj_ebits[i] / adj_revs[i]) if adj_revs[i] > 0 else 0.0,
                nwc=adj_nwc[i],
                capex=adj_capex[i],
                depreciation=adj_dep[i],
                tax=adj_taxes[i],
                fcf=adj_fcfs[i],
            )
            for i in range(len(adj_revs))
        ]

        return ForecastResult(
            symbol=base.symbol,
            scenario=scenario,
            yearly_forecasts=yearly,
            confidence_score=base.confidence_score
            * (0.9 if scenario != ScenarioType.BASE else 1.0),
            effective_tax_rate=base.effective_tax_rate,
            projected_revenues=adj_revs,
            projected_ebits=adj_ebits,
            projected_nwc=adj_nwc,
            projected_capex=adj_capex,
            projected_depreciation=adj_dep,
            projected_taxes=adj_taxes,
            projected_fcfs=adj_fcfs,
        )
