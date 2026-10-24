from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class ForecastMethod(StrEnum):
    CAGR = "CAGR"
    LINEAR_REGRESSION = "LINEAR_REGRESSION"
    ROLLING_AVERAGE = "ROLLING_AVERAGE"
    MEAN_REVERSION = "MEAN_REVERSION"


@dataclass(frozen=True)
class ForecastAssumption:
    method: ForecastMethod
    periods: int
    growth_rate: Decimal = Decimal("0.0")


@dataclass(frozen=True)
class ForecastResult:
    historical_values: tuple[Decimal, ...]
    projected_values: tuple[Decimal, ...]
    method: ForecastMethod
