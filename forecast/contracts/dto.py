from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from core.primitives import Currency


@dataclass(frozen=True)
class ForecastRequestDTO:
    """Input data transfer contract for generating a financial forecast."""

    ticker: str
    horizon_periods: int
    confidence_level: Decimal
    base_amount: Decimal
    currency: Currency

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "horizon_periods": self.horizon_periods,
            "confidence_level": str(self.confidence_level),
            "base_amount": str(self.base_amount),
            "currency": self.currency.code,
        }


@dataclass(frozen=True)
class ForecastResultDTO:
    """Output data transfer contract containing projection results."""

    ticker: str
    projected_value: Decimal
    lower_bound: Decimal
    upper_bound: Decimal
    currency: Currency

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "projected_value": str(self.projected_value),
            "lower_bound": str(self.lower_bound),
            "upper_bound": str(self.upper_bound),
            "currency": self.currency.code,
        }
