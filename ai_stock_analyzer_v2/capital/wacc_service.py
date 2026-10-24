from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class WACCOutput:
    wacc: float
    cost_of_equity: float
    cost_of_debt_post_tax: float
    equity_weight: float
    debt_weight: float


class WACCService:
    @staticmethod
    def compute_wacc(
        risk_free_rate: float,
        beta: float,
        equity_risk_premium: float,
        pre_tax_cost_of_debt: float,
        tax_rate: float,
        market_cap: float,
        total_debt: float,
    ) -> WACCOutput:
        cost_of_equity = risk_free_rate + (beta * equity_risk_premium)
        cost_of_debt_post_tax = pre_tax_cost_of_debt * (1.0 - tax_rate)

        total_capital = market_cap + total_debt
        equity_weight = market_cap / total_capital if total_capital > 0 else 0.80
        debt_weight = total_debt / total_capital if total_capital > 0 else 0.20

        wacc = (equity_weight * cost_of_equity) + (debt_weight * cost_of_debt_post_tax)

        return WACCOutput(
            wacc=round(wacc, 4),
            cost_of_equity=round(cost_of_equity, 4),
            cost_of_debt_post_tax=round(cost_of_debt_post_tax, 4),
            equity_weight=round(equity_weight, 4),
            debt_weight=round(debt_weight, 4),
        )
