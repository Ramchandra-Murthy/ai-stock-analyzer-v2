from __future__ import annotations

"""
==========================================================
DCF VALUATION ENGINE
Module  : dcf_model
Version : V3.0
==========================================================

Institutional Discounted Cash Flow (DCF) valuation engine.

Pipeline
--------
Validate
    ↓
Forecast
    ↓
Discount Explicit FCFF
    ↓
Terminal Value
    ↓
Enterprise Value
    ↓
Equity Value
    ↓
Sensitivity Analysis
    ↓
Return DCFResult

Contains no embedded financial formulas other than
high-level orchestration.
"""

from .dcf_input import DCFInput
from .dcf_result import DCFResult
from .discounting import build_discount_schedule
from .forecast import build_forecast_schedule
from .sensitivity import build_sensitivity_matrix
from .terminal_value import build_terminal_value
from .validation import validate_input


class DCFModel:
    """
    Institutional FCFF DCF valuation model.
    """

    def __init__(self, data: DCFInput):
        self.data = data

    # ======================================================
    # WACC
    # ======================================================

    def calculate_wacc(self) -> float:

        return (
            self.data.equity_weight * self.data.cost_of_equity
            + self.data.debt_weight * self.data.cost_of_debt_post_tax
        )

    # ======================================================
    # Main Valuation
    # ======================================================

    def run_model(self) -> DCFResult:

        # ------------------------------------------
        # Validation
        # ------------------------------------------

        validate_input(self.data)

        # ------------------------------------------
        # WACC
        # ------------------------------------------

        wacc = self.calculate_wacc()

        # ------------------------------------------
        # Forecast
        # ------------------------------------------

        forecast = build_forecast_schedule(self.data)

        # ------------------------------------------
        # Discount Explicit Cash Flows
        # ------------------------------------------

        discount = build_discount_schedule(
            projected_fcff=forecast.projected_fcff,
            wacc=wacc,
        )

        # ------------------------------------------
        # Terminal Value
        # ------------------------------------------

        terminal = build_terminal_value(
            final_year_fcff=forecast.projected_fcff[-1],
            wacc=wacc,
            terminal_growth_rate=self.data.terminal_growth_rate,
            forecast_years=self.data.forecast_years,
            pv_fcff_total=discount.pv_fcff_total,
        )

        # ------------------------------------------
        # Enterprise Value
        # ------------------------------------------

        enterprise_value = discount.pv_fcff_total + terminal.present_value_terminal

        # ------------------------------------------
        # Equity Bridge
        # ------------------------------------------

        equity_value = enterprise_value - self.data.total_debt + self.data.cash_and_equivalents

        implied_share_price = equity_value / self.data.shares_outstanding

        # ------------------------------------------
        # Sensitivity
        # ------------------------------------------

        sensitivity = build_sensitivity_matrix(
            final_year_fcff=forecast.projected_fcff[-1],
            pv_fcff_total=discount.pv_fcff_total,
            base_wacc=wacc,
            base_terminal_growth=self.data.terminal_growth_rate,
            forecast_years=self.data.forecast_years,
            debt=self.data.total_debt,
            cash=self.data.cash_and_equivalents,
            shares=self.data.shares_outstanding,
        )

        # ------------------------------------------
        # Assemble Result
        # ------------------------------------------

        return DCFResult(
            wacc=wacc,
            projected_revenue=forecast.projected_revenue,
            projected_ebit=forecast.projected_ebit,
            projected_nopat=forecast.projected_nopat,
            projected_fcff=forecast.projected_fcff,
            discount_factors=discount.discount_factors,
            present_value_fcff=discount.present_value_fcff,
            pv_fcff_total=discount.pv_fcff_total,
            terminal_fcff=terminal.terminal_fcff,
            terminal_value=terminal.terminal_value,
            present_value_terminal=terminal.present_value_terminal,
            terminal_value_pct_of_ev=terminal.terminal_value_pct_of_ev,
            enterprise_value=enterprise_value,
            total_debt=self.data.total_debt,
            cash_and_equivalents=self.data.cash_and_equivalents,
            equity_value=equity_value,
            shares_outstanding=self.data.shares_outstanding,
            implied_share_price=implied_share_price,
            forecast_period=self.data.forecast_years,
            currency=self.data.currency,
            company_name=self.data.company_name,
            validation_passed=True,
            warnings=[],
            sensitivity_matrix={
                "wacc_axis": sensitivity.wacc_axis,
                "terminal_growth_axis": sensitivity.terminal_growth_axis,
                "price_matrix": sensitivity.implied_share_price_matrix,
            },
        )
