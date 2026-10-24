from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.valuation.dcf import DCFInput, DCFModel, DCFResult


@dataclass(frozen=True)
class SOTPSegmentResult:
    segment_name: str
    valuation_method: str  # e.g., "DCF", "EV/EBITDA", "Book Value"
    enterprise_value: float
    equity_value: float
    net_debt: float
    weight: float = 1.00
    notes: str = ""


@dataclass(frozen=True)
class SOTPValuationOutput:
    company_name: str
    segments: list[SOTPSegmentResult]
    total_enterprise_value: float
    total_equity_value: float
    implied_share_price: float
    shares_outstanding: float
    diagnostics: dict[str, Any] = field(default_factory=dict)


class SOTPLongTermValuationService:
    """Enterprise-grade Sum-of-the-Parts (SOTP) Valuation Service."""

    def __init__(self, company_name: str, shares_outstanding: float):
        self.company_name = company_name
        self.shares_outstanding = shares_outstanding

    def evaluate_dcf_segment(self, segment_params: dict[str, Any]) -> SOTPSegmentResult:
        dcf_input = DCFInput(
            company_name=segment_params.get("segment_name", self.company_name),
            currency=segment_params.get("currency", "INR"),
            last_historical_revenue=segment_params.get("last_historical_revenue", 1000.0),
            revenue_growth_rates=segment_params.get(
                "revenue_growth_rates", [0.10, 0.10, 0.08, 0.08, 0.06]
            ),
            ebit_margins=segment_params.get("ebit_margins", [0.20, 0.20, 0.22, 0.22, 0.25]),
            tax_rate=segment_params.get("tax_rate", 0.25),
            working_capital_ratios=segment_params.get("working_capital_ratios", [0.15] * 5),
            sales_to_capital_ratios=segment_params.get("sales_to_capital_ratios", [2.0] * 5),
            cost_of_capital=segment_params.get("cost_of_capital", 0.10),
            terminal_growth_rate=segment_params.get("terminal_growth_rate", 0.04),
        )
        dcf_model = DCFModel(dcf_input)
        dcf_result: DCFResult = dcf_model.evaluate()

        ev = dcf_result.enterprise_value
        net_debt = segment_params.get("net_debt", 0.0)
        equity_val = ev - net_debt

        return SOTPSegmentResult(
            segment_name=segment_params.get("segment_name", "Core Segment"),
            valuation_method="DCF",
            enterprise_value=ev,
            equity_value=equity_val,
            net_debt=net_debt,
            weight=segment_params.get("weight", 1.0),
            notes="Evaluated via institutional multi-stage DCF model",
        )

    def evaluate_sotp(
        self,
        dcf_segments_raw: list[dict[str, Any]],
        other_segments_raw: list[dict[str, Any]] | None = None,
        holdco_discount: float = 0.0,
    ) -> SOTPValuationOutput:
        segment_results: list[SOTPSegmentResult] = []
        sum_enterprise_value = 0.0
        sum_equity_value = 0.0

        for seg in dcf_segments_raw:
            res = self.evaluate_dcf_segment(seg)
            segment_results.append(res)
            sum_enterprise_value += res.enterprise_value * res.weight
            sum_equity_value += res.equity_value * res.weight

        if other_segments_raw:
            for seg in other_segments_raw:
                ev = seg.get("enterprise_value", 0.0)
                nd = seg.get("net_debt", 0.0)
                eq = ev - nd
                wt = seg.get("weight", 1.0)
                res = SOTPSegmentResult(
                    segment_name=seg.get("segment_name", "Other Segment"),
                    valuation_method=seg.get("valuation_method", "Comparable / NAV"),
                    enterprise_value=ev,
                    equity_value=eq,
                    net_debt=nd,
                    weight=wt,
                    notes=seg.get("notes", ""),
                )
                segment_results.append(res)
                sum_enterprise_value += ev * wt
                sum_equity_value += eq * wt

        if holdco_discount > 0.0:
            sum_equity_value *= 1.0 - holdco_discount

        implied_price = (
            sum_equity_value / self.shares_outstanding if self.shares_outstanding > 0 else 0.0
        )

        return SOTPValuationOutput(
            company_name=self.company_name,
            segments=segment_results,
            total_enterprise_value=sum_enterprise_value,
            total_equity_value=sum_equity_value,
            implied_share_price=implied_price,
            shares_outstanding=self.shares_outstanding,
            diagnostics={
                "holdco_discount_applied": holdco_discount,
                "segment_count": len(segment_results),
            },
        )
