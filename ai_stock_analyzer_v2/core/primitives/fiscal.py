from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from core.primitives.value_object import ValueObject


class Frequency(StrEnum):
    """Standard reporting frequencies for institutional equity research."""

    ANNUAL = "ANNUAL"
    QUARTERLY = "QUARTERLY"
    MONTHLY = "MONTHLY"
    TTM = "TTM"


@dataclass(frozen=True, order=True)
class FiscalPeriod(ValueObject):
    """Immutable representation of a fiscal period (e.g., FY2025, Q3-2025)."""

    year: int
    quarter: int | None = None
    frequency: Frequency = Frequency.ANNUAL

    def __post_init__(self) -> None:
        if self.year < 1900 or self.year > 2100:
            raise ValueError(f"Invalid fiscal year: {self.year}")
        if self.frequency == Frequency.QUARTERLY:
            if self.quarter is None or not (1 <= self.quarter <= 4):
                raise ValueError(
                    f"Quarterly frequency requires quarter between 1 and 4, got {self.quarter}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "quarter": self.quarter,
            "frequency": self.frequency.value,
        }
