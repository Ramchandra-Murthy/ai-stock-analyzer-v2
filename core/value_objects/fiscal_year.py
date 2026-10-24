from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.primitives.base import ValueObject


@dataclass(frozen=True, order=True)
class FiscalYear(ValueObject):
    """Immutable representation of a fiscal year (e.g., FY2026)."""

    year: int

    def __post_init__(self) -> None:
        if not isinstance(self.year, int):
            object.__setattr__(self, "year", int(self.year))
        if self.year < 1900 or self.year > 2100:
            raise ValueError(f"Fiscal year out of valid operational bounds: {self.year}")

    def __str__(self) -> str:
        return f"FY{self.year}"

    def to_dict(self) -> dict[str, Any]:
        return {"fiscal_year": self.year}
