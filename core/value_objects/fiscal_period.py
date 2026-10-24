from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.primitives.base import ValueObject
from core.value_objects.fiscal_quarter import FiscalQuarter, QuarterEnum
from core.value_objects.fiscal_year import FiscalYear


@dataclass(frozen=True, order=True)
class FiscalPeriod(ValueObject):
    """Combined representation of a fiscal year and quarter (e.g., FY2026-Q1)."""

    year: FiscalYear
    quarter: FiscalQuarter

    @classmethod
    def from_ints(cls, year: int, quarter_str: str) -> FiscalPeriod:
        return cls(FiscalYear(year), FiscalQuarter(QuarterEnum(quarter_str.upper())))

    def __str__(self) -> str:
        return f"{self.year}-{self.quarter}"

    def to_dict(self) -> dict[str, Any]:
        return {"year": self.year.year, "quarter": str(self.quarter)}
