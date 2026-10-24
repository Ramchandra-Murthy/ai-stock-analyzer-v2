from __future__ import annotations

from typing import Any


class AIERPError(Exception):
    """Base exception for all AI Institutional Equity Research Platform errors."""


class PlatformError(AIERPError):
    """Compatibility base for platform exceptions, including structured details."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DomainError(PlatformError):
    """Base exception for business logic and domain validation errors."""


class CalculationError(DomainError):
    """Raised when a financial or quantitative calculation fails."""


class ValidationError(DomainError):
    """Raised when input parameters fail strict business rule validation."""


class RepositoryError(PlatformError):
    """Raised when a repository operation fails."""


class SerializationError(AIERPError):
    """Raised when data serialization or deserialization fails."""


class InfrastructureError(AIERPError):
    """Raised when external data sources, database connectors, or APIs fail."""
