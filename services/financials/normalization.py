from __future__ import annotations

"""
==========================================================
FINANCIAL STATEMENT NORMALIZATION
Module  : normalization
Version : V1.0
==========================================================

Converts raw financial statement data from different
providers into the platform's standardized financial
statement models.

Supported Sources
-----------------
• Annual Reports
• XBRL
• Yahoo Finance
• NSE/BSE APIs
• Alpha Vantage
• Manual Import
"""

from typing import Any

from services.financials.balance_sheet import BalanceSheet
from services.financials.cash_flow import CashFlowStatement
from services.financials.financial_statement import (
    FinancialStatements,
)
from services.financials.income_statement import IncomeStatement


def _get(
    data: dict[str, Any],
    *aliases: str,
    default: float = 0.0,
):
    """
    Returns the first matching field from multiple aliases.
    """
    for key in aliases:
        if key in data:
            return data[key]
    return default


def normalize_income_statement(
    raw: dict[str, Any],
) -> IncomeStatement:

    return IncomeStatement(
        revenue=_get(
            raw,
            "revenue",
            "totalRevenue",
            "Revenue",
        ),
        cost_of_goods_sold=_get(
            raw,
            "costOfRevenue",
            "cost_of_goods_sold",
            "COGS",
        ),
        ebitda=_get(
            raw,
            "ebitda",
            "EBITDA",
        ),
        ebit=_get(
            raw,
            "ebit",
            "operatingIncome",
        ),
        net_income=_get(
            raw,
            "netIncome",
            "profitAfterTax",
        ),
        depreciation_and_amortization=_get(
            raw,
            "depreciation",
            "depreciationAndAmortization",
        ),
        shares_outstanding=_get(
            raw,
            "sharesOutstanding",
        ),
    )


def normalize_balance_sheet(
    raw: dict[str, Any],
) -> BalanceSheet:

    return BalanceSheet(
        cash=_get(raw, "cash"),
        cash_equivalents=_get(
            raw,
            "cashEquivalents",
        ),
        short_term_investments=_get(
            raw,
            "shortTermInvestments",
        ),
        accounts_receivable=_get(
            raw,
            "accountsReceivable",
        ),
        inventory=_get(
            raw,
            "inventory",
        ),
        property_plant_equipment=_get(
            raw,
            "propertyPlantEquipment",
            "ppe",
        ),
        goodwill=_get(
            raw,
            "goodwill",
        ),
        intangible_assets=_get(
            raw,
            "intangibles",
        ),
        total_assets=_get(
            raw,
            "totalAssets",
        ),
        short_term_debt=_get(
            raw,
            "shortTermDebt",
        ),
        long_term_debt=_get(
            raw,
            "longTermDebt",
        ),
        total_liabilities=_get(
            raw,
            "totalLiabilities",
        ),
        total_equity=_get(
            raw,
            "totalEquity",
            "shareholdersEquity",
        ),
    )


def normalize_cash_flow(
    raw: dict[str, Any],
) -> CashFlowStatement:

    return CashFlowStatement(
        operating_cash_flow=_get(
            raw,
            "operatingCashFlow",
        ),
        capital_expenditure=_get(
            raw,
            "capitalExpenditure",
            "capex",
        ),
        investing_cash_flow=_get(
            raw,
            "investingCashFlow",
        ),
        financing_cash_flow=_get(
            raw,
            "financingCashFlow",
        ),
        dividends_paid=_get(
            raw,
            "dividendsPaid",
        ),
        net_change_in_cash=_get(
            raw,
            "changeInCash",
        ),
        ending_cash=_get(
            raw,
            "endingCash",
        ),
    )


def normalize_financial_statements(
    company_name: str,
    ticker: str,
    currency: str,
    fiscal_year: str,
    income_raw: dict[str, Any],
    balance_raw: dict[str, Any],
    cashflow_raw: dict[str, Any],
) -> FinancialStatements:
    """
    Builds the platform's canonical FinancialStatements object.
    """

    return FinancialStatements(
        company_name=company_name,
        ticker=ticker,
        currency=currency,
        fiscal_year=fiscal_year,
        income_statement=normalize_income_statement(income_raw),
        balance_sheet=normalize_balance_sheet(balance_raw),
        cash_flow_statement=normalize_cash_flow(cashflow_raw),
    )
