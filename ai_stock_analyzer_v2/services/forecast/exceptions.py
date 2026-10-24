from __future__ import annotations

from core.exceptions import ValidationError as CoreValidationError


class ForecastError(Exception):
    """Base exception for all forecast-related errors."""


class ForecastValidationError(ForecastError, CoreValidationError):
    """Raised when forecast input data fails validation checks."""


class ForecastAlgorithmError(ForecastError):
    """Raised when a forecasting algorithm encounters a calculation failure."""


class ForecastConfigurationError(ForecastError):
    """Raised when the forecast service is incorrectly configured."""


class ForecastSerializationError(ForecastError):
    """Raised when serialization or deserialization of forecast data fails."""


class ValuationError(ForecastValidationError):
    """Legacy validation exception, compatible with core ValidationError."""
