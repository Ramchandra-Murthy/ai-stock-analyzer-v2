from __future__ import annotations

"""
==========================================================
FINANCIAL RATIO ENGINE
Module  : financial_ratios
Version : V1.0
==========================================================

Computes standardized financial ratios from the
Financial Statement Layer.

Used by:
• DCF
• NAV
• Comparable
• Market Value
• Book Value
• Research Reports
• Screening Engine
"""

from dataclasses import dataclass

from services.financials.balance_sheet import BalanceSheet
from services.financials.cash_flow import CashFlowStatement
from services.financials.income_statement import IncomeStatement

# =========================================================
# Ratio Container
# =========================================================


@dataclass(slots=True)
class FinancialRatios:

    # Profitability
    gross_margin: float
    ebitda_margin: float
    ebit_margin: float
    net_margin: float

    # Returns
    roe: float
    roa: float
    roce: float
    roic: float

    # Liquidity
    current_ratio: float
    quick_ratio: float

    # Leverage
    debt_to_equity: float
    net_debt_to_ebitda: float

    # Cash Flow
    fcf_margin: float
    cash_conversion_ratio: float

    # Efficiency
    asset_turnover: float
    inventory_turnover: float


# =========================================================
# Helper
# =========================================================


def _safe_divide(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return a / b


# =========================================================
# Main Calculator
# =========================================================


def calculate_financial_ratios(
    income: IncomeStatement,
    balance: BalanceSheet,
    cashflow: CashFlowStatement,
) -> FinancialRatios:

    gross_profit = income.revenue - income.cost_of_goods_sold

    invested_capital = balance.total_equity + balance.total_debt - balance.total_cash

    current_ratio = _safe_divide(
        balance.total_current_assets,
        balance.total_current_liabilities,
    )

    quick_assets = balance.total_cash + balance.accounts_receivable

    quick_ratio = _safe_divide(
        quick_assets,
        balance.total_current_liabilities,
    )

    return FinancialRatios(
        # Profitability
        gross_margin=_safe_divide(
            gross_profit,
            income.revenue,
        ),
        ebitda_margin=_safe_divide(
            income.ebitda,
            income.revenue,
        ),
        ebit_margin=_safe_divide(
            income.ebit,
            income.revenue,
        ),
        net_margin=_safe_divide(
            income.net_income,
            income.revenue,
        ),
        # Returns
        roe=_safe_divide(
            income.net_income,
            balance.total_equity,
        ),
        roa=_safe_divide(
            income.net_income,
            balance.total_assets,
        ),
        roce=_safe_divide(
            income.ebit,
            invested_capital,
        ),
        roic=_safe_divide(
            income.ebit * (1 - 0.25),
            invested_capital,
        ),
        # Liquidity
        current_ratio=current_ratio,
        quick_ratio=quick_ratio,
        # Leverage
        debt_to_equity=_safe_divide(
            balance.total_debt,
            balance.total_equity,
        ),
        net_debt_to_ebitda=_safe_divide(
            balance.net_debt,
            income.ebitda,
        ),
        # Cash Flow
        fcf_margin=_safe_divide(
            cashflow.free_cash_flow,
            income.revenue,
        ),
        cash_conversion_ratio=_safe_divide(
            cashflow.operating_cash_flow,
            income.net_income,
        ),
        # Efficiency
        asset_turnover=_safe_divide(
            income.revenue,
            balance.total_assets,
        ),
        inventory_turnover=_safe_divide(
            income.cost_of_goods_sold,
            balance.inventory,
        ),
    )
