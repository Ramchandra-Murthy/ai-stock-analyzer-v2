from __future__ import annotations

from typing import Any

from services.valuation.base_engine import BaseValuationEngine
from services.valuation.contracts import SOTPSegmentInput
from services.valuation.dcf import DCFInput, DCFModel, DCFResult
from services.valuation.models import ValuationMethod, ValuationResult, ValuationStatus


class DCFValuationEngine(BaseValuationEngine):
    """Adapter wrapping the standalone DCF package into the unified engine interface."""

    @property
    def valuation_method(self) -> str:
        return ValuationMethod.DCF.value

    def value(self, entity: Any) -> ValuationResult:
        if isinstance(entity, SOTPSegmentInput):
            dcf_input = DCFInput(
                last_historical_revenue=entity.last_historical_revenue,
                revenue_growth_rates=entity.revenue_growth_rates,
                ebit_margin_forecast=entity.ebit_margin_forecast,
                dna_pct_rev=entity.dna_pct_rev,
                capex_pct_rev=entity.capex_pct_rev,
                nwc_pct_rev=entity.nwc_pct_rev,
                tax_rate=entity.tax_rate,
                cost_of_equity=entity.cost_of_equity,
                cost_of_debt_post_tax=entity.cost_of_debt_post_tax,
                equity_weight=entity.equity_weight,
                debt_weight=entity.debt_weight,
                terminal_growth_rate=entity.terminal_growth_rate,
                total_debt=entity.segment_debt,
                cash_and_equivalents=entity.segment_cash,
                shares_outstanding=entity.shares_outstanding,
                company_name=entity.segment_name,
                currency=entity.currency,
            )
        else:
            dcf_input = entity

        dcf_result: DCFResult = DCFModel(dcf_input).run_model()

        return ValuationResult(
            entity_name=dcf_input.company_name,
            valuation_method=ValuationMethod.DCF,
            valuation_status=ValuationStatus.COMPLETE,
            enterprise_value=dcf_result.enterprise_value,
            equity_value=dcf_result.equity_value,
            diagnostics={
                "currency": dcf_input.currency,
                "implied_share_price": dcf_result.implied_share_price,
                "wacc": dcf_result.wacc,
                "terminal_value_pct": dcf_result.terminal_value_pct_of_ev,
                "forecast_years": dcf_result.forecast_period,
            },
            raw_result=dcf_result,
        )
