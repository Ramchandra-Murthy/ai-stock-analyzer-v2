from __future__ import annotations

"""
==========================================================
BALANCE SHEET MODEL
Module  : balance_sheet
Version : V1.0
==========================================================

Defines a standardized Balance Sheet object.

This model serves as the canonical source for financial
position data across the valuation platform.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class BalanceSheet:
    """
    Standardized balance sheet.

    Represents one reporting period.
    """

    # ======================================================
    # Current Assets
    # ======================================================

    cash: float = 0.0
    cash_equivalents: float = 0.0
    short_term_investments: float = 0.0
    accounts_receivable: float = 0.0
    inventory: float = 0.0
    other_current_assets: float = 0.0
    total_current_assets: float = 0.0

    # ======================================================
    # Non-Current Assets
    # ======================================================

    property_plant_equipment: float = 0.0
    right_of_use_assets: float = 0.0
    goodwill: float = 0.0
    intangible_assets: float = 0.0
    long_term_investments: float = 0.0
    associates_and_joint_ventures: float = 0.0
    deferred_tax_assets: float = 0.0
    other_non_current_assets: float = 0.0
    total_non_current_assets: float = 0.0

    # ======================================================
    # Total Assets
    # ======================================================

    total_assets: float = 0.0

    # ======================================================
    # Current Liabilities
    # ======================================================

    accounts_payable: float = 0.0
    short_term_debt: float = 0.0
    current_lease_liabilities: float = 0.0
    accrued_expenses: float = 0.0
    other_current_liabilities: float = 0.0
    total_current_liabilities: float = 0.0

    # ======================================================
    # Non-Current Liabilities
    # ======================================================

    long_term_debt: float = 0.0
    long_term_lease_liabilities: float = 0.0
    deferred_tax_liabilities: float = 0.0
    pension_liabilities: float = 0.0
    other_non_current_liabilities: float = 0.0
    total_non_current_liabilities: float = 0.0

    # ======================================================
    # Total Liabilities
    # ======================================================

    total_liabilities: float = 0.0

    # ======================================================
    # Equity
    # ======================================================

    share_capital: float = 0.0
    retained_earnings: float = 0.0
    reserves: float = 0.0
    minority_interest: float = 0.0
    total_equity: float = 0.0

    # ======================================================
    # Derived Metrics
    # ======================================================

    @property
    def total_debt(self) -> float:
        """
        Total interest-bearing debt.
        """
        return (
            self.short_term_debt
            + self.long_term_debt
            + self.current_lease_liabilities
            + self.long_term_lease_liabilities
        )

    @property
    def total_cash(self) -> float:
        """
        Cash and near-cash resources.
        """
        return self.cash + self.cash_equivalents + self.short_term_investments

    @property
    def net_debt(self) -> float:
        """
        Net debt used by DCF and SOTP.
        """
        return self.total_debt - self.total_cash

    @property
    def debt_to_equity(self) -> float:
        """
        Debt-to-Equity Ratio.
        """
        if self.total_equity == 0:
            return 0.0

        return self.total_debt / self.total_equity
