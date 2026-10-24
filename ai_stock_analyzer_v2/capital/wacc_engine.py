from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValuationError
from core.logger import logger


@dataclass(slots=True, frozen=True)
class CAPMOutput:
    cost_of_equity: float
    cost_of_debt_post_tax: float
    equity_weight: float
    debt_weight: float
    wacc: float


class CapitalCostEngine:
    @staticmethod
    def calculate_wacc(
        risk_free_rate: float,
        beta: float,
        equity_risk_premium: float,
        pre_tax_cost_of_debt: float,
        tax_rate: float,
        market_cap: float,
        total_debt: float,
    ) -> CAPMOutput:
        if risk_free_rate < 0 or equity_risk_premium < 0:
            raise ValuationError("Risk-free rate and ERP must be non-negative.")

        cost_of_equity = risk_free_rate + (beta * equity_risk_premium)
        cost_of_debt_post_tax = pre_tax_cost_of_debt * (1.0 - tax_rate)

        total_capital = market_cap + total_debt
        equity_weight = market_cap / total_capital if total_capital > 0 else 0.80
        debt_weight = total_debt / total_capital if total_capital > 0 else 0.20

        wacc = (equity_weight * cost_of_equity) + (debt_weight * cost_of_debt_post_tax)

        if wacc <= 0:
            raise ValuationError("WACC must be positive.")

        logger.info(
            f"[CAPITAL_COST] Ke: {cost_of_equity:.2%} | Kd: {cost_of_debt_post_tax:.2%} | WACC: {wacc:.2%}"
        )

        return CAPMOutput(
            cost_of_equity=round(cost_of_equity, 4),
            cost_of_debt_post_tax=round(cost_of_debt_post_tax, 4),
            equity_weight=round(equity_weight, 4),
            debt_weight=round(debt_weight, 4),
            wacc=round(wacc, 4),
        )
