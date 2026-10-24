from __future__ import annotations

"""
==========================================================
FINANCIAL STATEMENT VALIDATOR
Module  : validator
Version : V1.0
==========================================================

Validates standardized FinancialStatements before they
are consumed by valuation models.

Validation Categories
---------------------
• Required Fields
• Accounting Identity
• Financial Consistency
• Data Quality
"""

from services.financials.financial_statement import (
    FinancialStatements,
)

# =========================================================
# Configuration
# =========================================================

ACCOUNTING_TOLERANCE = 1e-3

# =========================================================
# Helper
# =========================================================


def _require_non_negative(name: str, value: float) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")


# =========================================================
# Main Validation
# =========================================================


def validate_financial_statements(
    fs: FinancialStatements,
) -> None:

    income = fs.income_statement
    balance = fs.balance_sheet
    cashflow = fs.cash_flow_statement

    # ------------------------------------------------------
    # Required Fields
    # ------------------------------------------------------

    if not fs.company_name.strip():
        raise ValueError("Company name is required.")

    if not fs.ticker.strip():
        raise ValueError("Ticker is required.")

    # ------------------------------------------------------
    # Income Statement
    # ------------------------------------------------------

    _require_non_negative(
        "Revenue",
        income.revenue,
    )

    _require_non_negative(
        "Shares Outstanding",
        income.shares_outstanding,
    )

    # ------------------------------------------------------
    # Balance Sheet
    # ------------------------------------------------------

    _require_non_negative(
        "Total Assets",
        balance.total_assets,
    )

    _require_non_negative(
        "Total Liabilities",
        balance.total_liabilities,
    )

    _require_non_negative(
        "Total Equity",
        balance.total_equity,
    )

    # ------------------------------------------------------
    # Accounting Equation
    # ------------------------------------------------------

    difference = abs(balance.total_assets - (balance.total_liabilities + balance.total_equity))

    if difference > ACCOUNTING_TOLERANCE:
        raise ValueError(
            "Accounting equation failed.\n"
            f"Assets={balance.total_assets}\n"
            f"Liabilities+Equity="
            f"{balance.total_liabilities + balance.total_equity}"
        )

    # ------------------------------------------------------
    # Cash Flow
    # ------------------------------------------------------

    calculated_cash = cashflow.beginning_cash + cashflow.net_change_in_cash

    if cashflow.beginning_cash != 0 or cashflow.ending_cash != 0:
        difference = abs(calculated_cash - cashflow.ending_cash)

        if difference > ACCOUNTING_TOLERANCE:
            raise ValueError("Cash Flow reconciliation failed.")
