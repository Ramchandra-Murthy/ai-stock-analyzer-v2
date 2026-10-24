from __future__ import annotations

"""
==========================================================
DCF RESULT MODEL
Module  : dcf_result
Version : V2.0
==========================================================

Defines the standardized output produced by the
Discounted Cash Flow (DCF) valuation engine.

This module contains no valuation logic.
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class DCFResult:
    """
    Standard output produced by the DCF valuation engine.
    """

    # ======================================================
    # Discount Rate
    # ======================================================

    wacc: float

    # ======================================================
    # Revenue Forecast
    # ======================================================

    projected_revenue: list[float]

    # ======================================================
    # Operating Forecast
    # ======================================================

    projected_ebit: list[float]

    projected_nopat: list[float]

    # ======================================================
    # Free Cash Flow Forecast
    # ======================================================

    projected_fcff: list[float]

    discount_factors: list[float]

    present_value_fcff: list[float]

    pv_fcff_total: float

    # ======================================================
    # Terminal Value
    # ======================================================

    terminal_fcff: float

    terminal_value: float

    present_value_terminal: float

    terminal_value_pct_of_ev: float

    # ======================================================
    # Enterprise Value Bridge
    # ======================================================

    enterprise_value: float

    total_debt: float

    cash_and_equivalents: float

    equity_value: float

    # ======================================================
    # Per Share Valuation
    # ======================================================

    shares_outstanding: float

    implied_share_price: float

    # ======================================================
    # Forecast Metadata
    # ======================================================

    forecast_period: int

    currency: str = "INR"

    company_name: str = ""

    # ======================================================
    # Validation
    # ======================================================

    validation_passed: bool = True

    warnings: list[str] = field(default_factory=list)

    # ======================================================
    # Sensitivity Analysis
    # ======================================================

    sensitivity_matrix: dict[str, object] = field(default_factory=dict)

    # ======================================================
    # Convenience Properties
    # ======================================================

    @property
    def discrete_value(self) -> float:
        """Present value of explicit forecast cash flows."""
        return self.pv_fcff_total

    @property
    def terminal_value_contribution(self) -> float:
        """Contribution of terminal value to enterprise value."""
        return self.present_value_terminal

    @property
    def enterprise_bridge(self) -> dict[str, float]:
        """Enterprise value bridge."""
        return {
            "enterprise_value": self.enterprise_value,
            "less_debt": self.total_debt,
            "add_cash": self.cash_and_equivalents,
            "equity_value": self.equity_value,
        }

    def summary(self) -> dict[str, float]:
        """
        Returns a concise valuation summary.
        """
        return {
            "wacc": self.wacc,
            "enterprise_value": self.enterprise_value,
            "equity_value": self.equity_value,
            "share_price": self.implied_share_price,
            "terminal_value_pct": self.terminal_value_pct_of_ev,
        }
