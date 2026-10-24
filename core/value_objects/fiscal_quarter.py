from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from core.primitives.base import ValueObject


class QuarterEnum(StrEnum):
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"
    FY = "FY"


@dataclass(frozen=True, order=True)
class FiscalQuarter(ValueObject):
    """Immutable representation of a fiscal quarter or annual period."""

    quarter: QuarterEnum

    def __post_init__(self) -> None:
        if isinstance(self.quarter, str):
            object.__setattr__(self, "quarter", QuarterEnum(self.quarter.upper()))

    def __str__(self) -> str:
        return self.quarter.value

    def to_dict(self) -> dict[str, Any]:
        return {"fiscal_quarter": self.quarter.value}
