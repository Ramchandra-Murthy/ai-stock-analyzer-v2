from __future__ import annotations

from .base import (
    AIERPError,
    CalculationError,
    DomainError,
    InfrastructureError,
    PlatformError,
    RepositoryError,
    SerializationError,
    ValidationError,
)
from .forecast import ForecastError
from .valuation import ValuationError

AIStockAnalyzerError = AIERPError

__all__ = [
    "AIStockAnalyzerError",
    "AIERPError",
    "PlatformError",
    "DomainError",
    "CalculationError",
    "ValidationError",
    "RepositoryError",
    "ValuationError",
    "SerializationError",
    "InfrastructureError",
    "ForecastError",
]
