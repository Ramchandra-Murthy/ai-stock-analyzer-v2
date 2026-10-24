"""
==========================================================
EQUITY VALUATION PLATFORM v5.2
Module  : services.wacc.wacc_service
Layer   : Services / WACC
Summary : Capital Cost Calculation Engine executing CAPM, WACC,
          and Hamada Beta adjustments.
==========================================================
"""

from __future__ import annotations

from core.logger import logger
from services.wacc.wacc_models import (
    BetaAdjustmentInput,
    CAPMInput,
    WACCInput,
    WACCResult,
)


class CapitalCostEngine:
    """Orchestrates Cost of Equity, WACC, and Beta adjustment calculations."""

    def calculate_cost_of_equity(self, inp: CAPMInput) -> float:
        """Calculates Cost of Equity via CAPM: Re = Rf + (Beta * ERP) + Size Premium."""
        cost_of_equity = (
            inp.risk_free_rate + (inp.beta * inp.equity_risk_premium) + inp.size_premium
        )
        logger.info(f"[CAPM] Cost of Equity calculated: {cost_of_equity:.4%}")
        return round(cost_of_equity, 6)

    def unlever_beta(self, inp: BetaAdjustmentInput) -> float:
        """Unlevers raw market beta using Hamada's equation."""
        unlevered = inp.levered_beta / (1.0 + (1.0 - inp.tax_rate) * inp.debt_to_equity_ratio)
        logger.info(f"[BETA ADJUST] Unlevered Beta calculated: {unlevered:.4f}")
        return round(unlevered, 4)

    def relever_beta(
        self, unlevered_beta: float, debt_to_equity_ratio: float, tax_rate: float
    ) -> float:
        """Relevers asset beta to target capital structure using Hamada's equation."""
        relevered = unlevered_beta * (1.0 + (1.0 - tax_rate) * debt_to_equity_ratio)
        logger.info(f"[BETA ADJUST] Relevered Beta calculated: {relevered:.4f}")
        return round(relevered, 4)

    def calculate_wacc(self, inp: WACCInput) -> WACCResult:
        """Calculates WACC using capital structure market weights."""
        total_value = inp.market_cap + inp.total_debt

        if total_value == 0:
            raise ValueError("Total capital structure value (E + D) cannot be zero.")

        w_e = inp.market_cap / total_value
        w_d = inp.total_debt / total_value

        after_tax_cost_of_debt = inp.cost_of_debt * (1.0 - inp.tax_rate)

        wacc = (w_e * inp.cost_of_equity) + (w_d * after_tax_cost_of_debt)

        logger.info(f"[WACC] {inp.symbol} WACC = {wacc:.4%} (E/V: {w_e:.2%}, D/V: {w_d:.2%})")

        return WACCResult(
            symbol=inp.symbol,
            wacc=round(wacc, 6),
            cost_of_equity=round(inp.cost_of_equity, 6),
            cost_of_debt_after_tax=round(after_tax_cost_of_debt, 6),
            equity_weight=round(w_e, 4),
            debt_weight=round(w_d, 4),
        )


WACCService = CapitalCostEngine
