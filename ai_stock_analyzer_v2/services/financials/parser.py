from __future__ import annotations

"""
==========================================================
FINANCIAL STATEMENT PARSER
Module  : parser
Version : V1.0
==========================================================

Entry point for importing financial statements into the
platform.

Pipeline
--------
Raw Data
    ↓
Normalization
    ↓
Validation
    ↓
Repository
    ↓
FinancialStatements
"""

from typing import Any

from services.financials.normalization import (
    normalize_financial_statements,
)
from services.financials.repository import (
    FinancialStatementRepository,
)
from services.financials.validator import (
    validate_financial_statements,
)

_repository = FinancialStatementRepository()


def parse_financial_statements(
    *,
    company_name: str,
    ticker: str,
    currency: str,
    fiscal_year: str,
    income_statement: dict[str, Any],
    balance_sheet: dict[str, Any],
    cash_flow: dict[str, Any],
):
    """
    Normalizes, validates and stores a FinancialStatements object.
    """

    statements = normalize_financial_statements(
        company_name=company_name,
        ticker=ticker,
        currency=currency,
        fiscal_year=fiscal_year,
        income_raw=income_statement,
        balance_raw=balance_sheet,
        cashflow_raw=cash_flow,
    )

    validate_financial_statements(statements)

    _repository.save(statements)

    return statements


def get_financial_statements(
    company_name: str,
    fiscal_year: str,
):
    """
    Retrieve previously parsed statements.
    """

    return _repository.load(
        company_name,
        fiscal_year,
    )


def repository():
    """
    Returns the singleton repository.
    """

    return _repository
