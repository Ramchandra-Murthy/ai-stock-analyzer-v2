from __future__ import annotations

import math
from dataclasses import dataclass

from core.enums import Status
from core.logger import logger
from services.sotp.sotp_engine import SOTPResult


@dataclass(slots=True, frozen=True)
class EquityResearchReport:
    ticker: str
    company_name: str
    current_price: float | None
    target_price: float | None
    recommendation: str
    investment_thesis: str
    sotp_result: SOTPResult
    status: Status = Status.OK


class ResearchReportGenerator:
    """Compiles structured institutional research reports from valuation outputs."""

    @staticmethod
    def generate_report(
        ticker: str,
        company_name: str,
        current_price: float | None,
        target_price: float | None,
        sotp_result: SOTPResult,
        investment_thesis: str,
        recommendation: str | None = None,
    ) -> EquityResearchReport:
        """Build a report without creating a second investment recommendation.

        The recommendation supplied by the authoritative decision layer is
        preserved. Invalid prices or unusable recommendation evidence are
        surfaced as an error rather than producing a misleading report.
        """

        valid_current = (
            isinstance(current_price, (int, float))
            and math.isfinite(float(current_price))
            and float(current_price) > 0
        )
        valid_target = (
            isinstance(target_price, (int, float))
            and math.isfinite(float(target_price))
            and float(target_price) > 0
        )
        usable_recommendation = bool(recommendation) and str(
            recommendation
        ).strip().upper() not in {"N/A", "UNKNOWN"}

        if not valid_current or not valid_target:
            rec = str(recommendation).strip() if usable_recommendation else "INSUFFICIENT DATA"
            return EquityResearchReport(
                ticker=ticker,
                company_name=company_name,
                current_price=current_price,
                target_price=target_price,
                recommendation=rec,
                investment_thesis=investment_thesis,
                sotp_result=sotp_result,
                status=Status.ERROR,
            )

        current = float(current_price)
        target = float(target_price)
        upside = (target - current) / current

        if usable_recommendation:
            rec = str(recommendation).strip()
            status = Status.OK
        else:
            rec = "INSUFFICIENT DATA"
            status = Status.ERROR

        logger.info(f"[{ticker}] Report generated. Recommendation: {rec} (Upside: {upside:.2%})")

        return EquityResearchReport(
            ticker=ticker,
            company_name=company_name,
            current_price=current,
            target_price=target,
            recommendation=rec,
            investment_thesis=investment_thesis,
            sotp_result=sotp_result,
            status=status,
        )
