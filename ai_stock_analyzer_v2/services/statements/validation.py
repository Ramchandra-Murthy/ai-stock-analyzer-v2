"""
==========================================================
FINANCIAL STATEMENT VALIDATOR
Module  : services.statements.validation
Layer   : Validation & Governance
==========================================================
"""

from __future__ import annotations

import math

from services.statements.models import FinancialStatementPackage


class StatementValidationError(Exception):
    """Raised when financial statement data fails validation rules."""

    pass


class StatementValidator:
    @staticmethod
    def validate_package(package: FinancialStatementPackage) -> None:
        if not package.ticker or not package.ticker.strip():
            raise StatementValidationError("Ticker symbol must be a non-empty string.")

        if not package.years:
            raise StatementValidationError("Statement years sequence cannot be empty.")

        # Validate Income Statement consistency
        for item_name, line_item in package.income_statement.items():
            if len(line_item.values) != len(package.years):
                raise StatementValidationError(
                    f"Income statement item '{item_name}' year count mismatch."
                )
            for yr, val in line_item.values.items():
                if math.isnan(val) or math.isinf(val):
                    raise StatementValidationError(
                        f"Invalid numeric value in income statement '{item_name}' for year {yr}."
                    )
