from __future__ import annotations

"""
==========================================================
FINANCIAL MODEL BUILDERS
Module  : builders
Version : V1.4
==========================================================

Transforms validated FinancialStatements into the specific
input contracts required by each valuation engine.
"""

from services.financials.financial_statement import FinancialStatements

# Comparable
from services.valuation.comparable.comparable_input import (
    ComparableInput,
    TargetCompany,
)

# DCF
from services.valuation.dcf.dcf_input import DCFInput

# NAV
from services.valuation.nav.nav_input import (
    NAVInput,
)

# =========================================================
# DCF Builder
# =========================================================


def build_dcf_input(
    fs: FinancialStatements,
) -> DCFInput:
    """
    Converts FinancialStatements into DCFInput.
    """

    income = fs.income_statement
    balance = fs.balance_sheet

    dna_ratio = income.depreciation_and_amortization / income.revenue if income.revenue > 0 else 0.0

    preferred_stock_val = getattr(balance, "preferred_stock", 0.0)

    return DCFInput(
        company_name=fs.company_name,
        currency=fs.currency,
        last_historical_revenue=income.revenue,
        revenue_growth_rates=[0.08] * 5,
        ebit_margin_forecast=[income.operating_margin()] * 5,
        capex_pct_rev=[0.05] * 5,
        nwc_pct_rev=[0.02] * 5,
        dna_pct_rev=[dna_ratio] * 5,
        tax_rate=0.25,
        equity_weight=0.80,
        debt_weight=0.20,
        cost_of_equity=0.12,
        cost_of_debt_post_tax=0.06,
        terminal_growth_rate=0.03,
        total_debt=balance.total_debt,
        cash_and_equivalents=balance.total_cash,
        shares_outstanding=income.shares_outstanding,
        minority_interest=balance.minority_interest,
        preferred_stock=preferred_stock_val,
    )


# =========================================================
# NAV Builder
# =========================================================


def build_nav_input(
    fs: FinancialStatements,
) -> NAVInput:
    """
    Converts FinancialStatements into NAVInput.
    """

    return NAVInput(
        company_name=fs.company_name,
        currency=fs.currency,
        assets=[],
        liabilities=[],
        minority_interest=fs.balance_sheet.minority_interest,
        holding_company_discount_pct=0.15,
        shares_outstanding=fs.income_statement.shares_outstanding,
    )


# =========================================================
# Comparable Builder
# =========================================================


def build_comparable_input(
    fs: FinancialStatements,
) -> ComparableInput:
    """
    Converts FinancialStatements into ComparableInput.
    """

    income = fs.income_statement
    balance = fs.balance_sheet

    target = TargetCompany(
        company_name=fs.company_name,
        revenue=income.revenue,
        ebit=income.ebit,
        ebitda=income.ebitda,
        net_income=income.net_income,
        book_value=balance.total_equity,
        net_debt=balance.net_debt,
        shares_outstanding=income.shares_outstanding,
    )

    return ComparableInput(
        target=target,
        peers=[],
        currency=fs.currency,
    )


# Compatibility Adapter for Legacy Test Suites
class ValuationPayloadBuilder:
    @staticmethod
    def build_dcf_input(*args, **kwargs):
        return build_dcf_input(*args, **kwargs)

    @staticmethod
    def build_nav_input(*args, **kwargs):
        return build_nav_input(*args, **kwargs)

    @staticmethod
    def build_comparable_input(*args, **kwargs):
        return build_comparable_input(*args, **kwargs)
