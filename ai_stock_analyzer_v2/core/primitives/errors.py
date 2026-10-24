from __future__ import annotations

from core.exceptions import DomainError, ValidationError


class PrimitiveTypeError(ValidationError):
    """Raised when a primitive receives an unexpected data type or format."""

    pass


class CurrencyMismatchError(DomainError):
    """Raised when performing arithmetic or comparisons between mismatched currencies."""

    pass
