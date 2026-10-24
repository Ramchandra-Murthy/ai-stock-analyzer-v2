from __future__ import annotations

"""
==========================================================
PLATFORM DOMAIN EXCEPTIONS
Module  : exceptions
Version : V3.0
==========================================================

Domain exception hierarchy for the AI Equity Valuation Platform.
"""


class ValuationPlatformError(Exception):
    """Base class for all equity valuation platform errors."""

    pass


class ValidationError(ValuationPlatformError):
    """Raised when input contract sanity or bounds checks fail."""

    pass


class FinancialDataError(ValuationPlatformError):
    """Raised when accounting identities fail or financial fields are missing."""

    pass


class ParserError(ValuationPlatformError):
    """Raised when XBRL, Annual Report, or filing ingestion fails."""

    pass


class ValuationError(ValuationPlatformError):
    """Raised when engine mathematical execution fails (e.g., negative WACC)."""

    pass


class DispatcherError(ValuationPlatformError):
    """Raised when a specified engine is unregistered or invalid payload given."""

    pass


class ReportGenerationError(ValuationPlatformError):
    """Raised when report synthesis or template rendering fails."""

    pass
