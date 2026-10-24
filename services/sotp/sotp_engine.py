from __future__ import annotations

from dataclasses import dataclass

from core.enums import Status, ValuationMethod
from core.exceptions import ValuationError
from core.logger import logger


@dataclass(slots=True, frozen=True)
class SegmentValuation:
    segment_name: str
    valuation_method: ValuationMethod
    value_amount: float
    stake_percentage: float = 1.00
    notes: str = ""


@dataclass(slots=True, frozen=True)
class SOTPInput:
    company_name: str
    currency: str
    segments: list[SegmentValuation]
    conglomerate_discount_pct: float = 0.0
    net_debt: float = 0.0
    shares_outstanding: float = 1.0


@dataclass(slots=True, frozen=True)
class SOTPResult:
    company_name: str
    gross_enterprise_value: float
    gross_equity_value: float
    net_equity_value: float
    value_per_share: float
    status: Status = Status.OK


class SOTPAggregator:
    """Aggregates multi-segment valuations into a consolidated Target Price per Share."""

    @staticmethod
    def calculate(sotp_input: SOTPInput) -> SOTPResult:
        if not sotp_input.segments:
            raise ValuationError("SOTP calculation requires at least one business segment.")

        gross_ev = sum(s.value_amount * s.stake_percentage for s in sotp_input.segments)
        gross_equity = gross_ev - sotp_input.net_debt
        net_equity = gross_equity * (1.0 - sotp_input.conglomerate_discount_pct)
        value_per_share = net_equity / max(sotp_input.shares_outstanding, 1e-4)

        logger.info(
            f"[{sotp_input.company_name}] Gross EV: {gross_ev:.2f} | Net Equity: {net_equity:.2f} | Per Share: {value_per_share:.2f}"
        )

        return SOTPResult(
            company_name=sotp_input.company_name,
            gross_enterprise_value=round(gross_ev, 2),
            gross_equity_value=round(gross_equity, 2),
            net_equity_value=round(net_equity, 2),
            value_per_share=round(value_per_share, 2),
        )
