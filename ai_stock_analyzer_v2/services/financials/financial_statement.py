from __future__ import annotations

"""
==========================================================
STANDARD FINANCIAL STATEMENT MODEL
Module  : financial_statement
Version : V1.0
==========================================================

Defines the master financial statement object used
throughout the valuation platform.
"""

from dataclasses import dataclass, field
from typing import Any

from services.financials.balance_sheet import BalanceSheet
from services.financials.cash_flow import CashFlowStatement
from services.financials.income_statement import IncomeStatement


@dataclass(slots=True)
class PeriodFinancials:
    """
    Holds statements for a single fiscal period.
    """

    period: str
    income_statement: IncomeStatement
    balance_sheet: BalanceSheet
    cash_flow_statement: CashFlowStatement


@dataclass(slots=True)
class FinancialStatements:
    """
    Standardized financial statement container.
    """

    company_name: str
    ticker: str
    currency: str
    fiscal_year: str
    income_statement: IncomeStatement
    balance_sheet: BalanceSheet
    cash_flow_statement: CashFlowStatement
    periods: list[PeriodFinancials] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "company": self.company_name,
            "year": self.fiscal_year,
            "revenue": self.income_statement.revenue,
            "ebit": self.income_statement.ebit,
            "net_income": self.income_statement.net_income,
            "cash": self.balance_sheet.total_cash,
            "debt": self.balance_sheet.total_debt,
        }
