from __future__ import annotations

from core.exceptions import ValuationError
from core.logger import logger
from services.capital.capital_models import CapitalStructure, WACCResult


class WACCService:
    """Computes Weighted Average Cost of Capital (WACC) via CAPM and post-tax cost of debt."""

    def compute_wacc(
        self,
        risk_free_rate: float,
        beta: float,
        equity_risk_premium: float,
        pre_tax_cost_of_debt: float,
        tax_rate: float,
        capital_structure: CapitalStructure,
    ) -> WACCResult:
        if risk_free_rate < 0 or equity_risk_premium < 0:
            raise ValuationError("Risk-free rate and ERP must be non-negative.")

        cost_of_equity = risk_free_rate + (beta * equity_risk_premium)
        post_tax_cost_of_debt = pre_tax_cost_of_debt * (1.0 - tax_rate)

        we = capital_structure.weight_equity
        wd = capital_structure.weight_debt

        wacc = (we * cost_of_equity) + (wd * post_tax_cost_of_debt)

        logger.info(
            f"[CAPITAL] Computed WACC: {wacc:.2%} (Ke: {cost_of_equity:.2%}, Kd_post: {post_tax_cost_of_debt:.2%}, We: {we:.1%}, Wd: {wd:.1%})"
        )

        return WACCResult(
            cost_of_equity=cost_of_equity,
            cost_of_debt_pre_tax=pre_tax_cost_of_debt,
            cost_of_debt_post_tax=post_tax_cost_of_debt,
            weight_equity=we,
            weight_debt=wd,
            effective_tax_rate=tax_rate,
            wacc=wacc,
        )
