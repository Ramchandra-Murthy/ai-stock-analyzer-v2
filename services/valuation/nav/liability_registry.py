from __future__ import annotations

"""
==========================================================
NAV LIABILITY REGISTRY
Module  : liability_registry
Version : V1.0
==========================================================

Central registry of supported liability categories used by
the NAV valuation engine.

Standardizes liability classification across:

    • NAV Model
    • SOTP Engine
    • Research Reports
    • Portfolio Analytics
"""

from enum import StrEnum

# ==========================================================
# Liability Categories
# ==========================================================


class LiabilityCategory(StrEnum):

    # Financial Debt
    SHORT_TERM_DEBT = "SHORT_TERM_DEBT"

    LONG_TERM_DEBT = "LONG_TERM_DEBT"

    LEASE_LIABILITY = "LEASE_LIABILITY"

    BONDS_PAYABLE = "BONDS_PAYABLE"

    BANK_BORROWINGS = "BANK_BORROWINGS"

    # Operating Liabilities
    TRADE_PAYABLES = "TRADE_PAYABLES"

    ACCRUED_EXPENSES = "ACCRUED_EXPENSES"

    PROVISIONS = "PROVISIONS"

    # Taxes
    CURRENT_TAX = "CURRENT_TAX"

    DEFERRED_TAX = "DEFERRED_TAX"

    # Employee Obligations
    PENSION = "PENSION"

    GRATUITY = "GRATUITY"

    # Contingent Items
    CONTINGENT_LIABILITY = "CONTINGENT_LIABILITY"

    LEGAL_CLAIMS = "LEGAL_CLAIMS"

    GUARANTEES = "GUARANTEES"

    # Minority Interest
    MINORITY_INTEREST = "MINORITY_INTEREST"

    # Other
    OTHER = "OTHER"


# ==========================================================
# Convenience Collections
# ==========================================================

FINANCIAL_LIABILITIES = {
    LiabilityCategory.SHORT_TERM_DEBT,
    LiabilityCategory.LONG_TERM_DEBT,
    LiabilityCategory.LEASE_LIABILITY,
    LiabilityCategory.BONDS_PAYABLE,
    LiabilityCategory.BANK_BORROWINGS,
}

OPERATING_LIABILITIES = {
    LiabilityCategory.TRADE_PAYABLES,
    LiabilityCategory.ACCRUED_EXPENSES,
    LiabilityCategory.PROVISIONS,
}

TAX_LIABILITIES = {
    LiabilityCategory.CURRENT_TAX,
    LiabilityCategory.DEFERRED_TAX,
}

EMPLOYEE_LIABILITIES = {
    LiabilityCategory.PENSION,
    LiabilityCategory.GRATUITY,
}

CONTINGENT_LIABILITIES = {
    LiabilityCategory.CONTINGENT_LIABILITY,
    LiabilityCategory.LEGAL_CLAIMS,
    LiabilityCategory.GUARANTEES,
}
