from __future__ import annotations

"""
==========================================================
CASH FLOW STATEMENT MODEL
Module  : cash_flow
Version : V1.0
==========================================================

Defines a standardized Cash Flow Statement object.

Represents cash generated and consumed during a reporting
period.

Used throughout:
• DCF
• Forecasting
• Financial Quality Analysis
• Research Reports
"""

from dataclasses import dataclass


@dataclass(slots=True)
class CashFlowStatement:
    """
    Standardized Cash Flow Statement.

    Represents one reporting period.
    """

    # ======================================================
    # Operating Activities
    # ======================================================

    net_income: float = 0.0
    depreciation_and_amortization: float = 0.0
    share_based_compensation: float = 0.0
    deferred_tax: float = 0.0
    change_in_working_capital: float = 0.0
    other_operating_items: float = 0.0
    operating_cash_flow: float = 0.0

    # ======================================================
    # Investing Activities
    # ======================================================

    capital_expenditure: float = 0.0
    acquisitions: float = 0.0
    asset_sales: float = 0.0
    investment_purchases: float = 0.0
    investment_sales: float = 0.0
    investing_cash_flow: float = 0.0

    # ======================================================
    # Financing Activities
    # ======================================================

    debt_issued: float = 0.0
    debt_repaid: float = 0.0
    dividends_paid: float = 0.0
    share_repurchases: float = 0.0
    equity_issued: float = 0.0
    financing_cash_flow: float = 0.0

    # ======================================================
    # Net Cash Movement
    # ======================================================

    net_change_in_cash: float = 0.0
    beginning_cash: float = 0.0
    ending_cash: float = 0.0

    # ======================================================
    # Derived Metrics
    # ======================================================

    @property
    def free_cash_flow(self) -> float:
        """
        Free Cash Flow (FCF).

        Formula:
            Operating Cash Flow - Capital Expenditure
        """
        return self.operating_cash_flow - self.capital_expenditure

    @property
    def reinvestment(self) -> float:
        """
        Total business reinvestment.

        Formula:
            CapEx + Acquisitions
        """
        return self.capital_expenditure + self.acquisitions

    @property
    def financing_requirement(self) -> float:
        """
        Net financing requirement.

        Positive -> Raised capital
        Negative -> Returned capital
        """
        return (
            self.debt_issued
            + self.equity_issued
            - self.debt_repaid
            - self.dividends_paid
            - self.share_repurchases
        )
