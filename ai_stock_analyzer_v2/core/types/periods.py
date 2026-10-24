from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class FiscalPeriod:
    year: int
    quarter: int | None = None

    def __post_init__(self) -> None:
        if self.year < 1900 or self.year > 2100:
            raise ValidationError(f"Invalid fiscal year: {self.year}")
        if self.quarter is not None and not (1 <= self.quarter <= 4):
            raise ValidationError(
                f"Invalid fiscal quarter: {self.quarter}. Must be between 1 and 4."
            )

    def __str__(self) -> str:
        if self.quarter is not None:
            return f"FY{self.year}-Q{self.quarter}"
        return f"FY{self.year}"
