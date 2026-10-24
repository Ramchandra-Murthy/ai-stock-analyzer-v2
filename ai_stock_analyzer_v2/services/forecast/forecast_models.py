"""Compatibility exports for the legacy forecast API.

Older forecast subservices import shared model and input contracts from this
module. The canonical model definitions live in ``services.forecast.models``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from services.forecast.models import (
    CapexForecast,
    ConfidenceLevel,
    DepreciationForecast,
    ForecastAssumption,
    ForecastConfidence,
    ForecastMethod,
    ForecastScenario,
    MarginForecast,
    RevenueForecast,
    TaxForecast,
    TerminalGrowthForecast,
    WorkingCapitalForecast,
)


class ScenarioType(StrEnum):
    BASE = "BASE"
    BULL = "BULL"
    BEAR = "BEAR"


@dataclass(frozen=True, slots=True)
class AlgorithmInput:
    """Normalized input passed to legacy forecasting algorithms."""

    historical_values: tuple[float, ...]
    forecast_periods: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "historical_values", tuple(float(value) for value in self.historical_values)
        )
        if self.forecast_periods < 1:
            raise ValueError("forecast_periods must be at least 1")


__all__ = [
    "AlgorithmInput",
    "CapexForecast",
    "ConfidenceLevel",
    "DepreciationForecast",
    "ForecastAssumption",
    "ForecastConfidence",
    "ForecastMethod",
    "ForecastScenario",
    "MarginForecast",
    "RevenueForecast",
    "ScenarioType",
    "TaxForecast",
    "TerminalGrowthForecast",
    "WorkingCapitalForecast",
]
