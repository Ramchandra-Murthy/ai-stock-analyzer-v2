from __future__ import annotations

"""
==========================================================
INCOME STATEMENT MODEL
Module  : income_statement
Version : V1.0
==========================================================

Defines a standardized Income Statement object.

This model serves as the canonical source for operating
performance metrics across the valuation platform.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class IncomeStatement:
    """
    Standardized income statement.

    Values should represent a single fiscal period.
    """

    # Revenue
    revenue: float
    other_operating_income: float = 0.0
    total_operating_income: float = 0.0

    # Expenses
    cost_of_goods_sold: float = 0.0
    operating_expenses: float = 0.0
    depreciation_and_amortization: float = 0.0

    # Operating Profit
    ebitda: float = 0.0
    ebit: float = 0.0

    # Financing
    finance_cost: float = 0.0
    finance_income: float = 0.0

    # Pre-tax
    profit_before_tax: float = 0.0
    tax_expense: float = 0.0

    # Bottom Line
    net_income: float = 0.0

    # Per Share
    shares_outstanding: float = 0.0
    eps: float = 0.0

    def operating_margin(self) -> float:
        """
        EBIT Margin
        """
        if self.revenue == 0:
            return 0.0
        return self.ebit / self.revenue

    def ebitda_margin(self) -> float:
        """
        EBITDA Margin
        """
        if self.revenue == 0:
            return 0.0
        return self.ebitda / self.revenue

    def net_margin(self) -> float:
        """
        Net Profit Margin
        """
        if self.revenue == 0:
            return 0.0
        return self.net_income / self.revenue
