from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, order=True)
class Percentage:
    """Immutable representation of a percentage value stored as a decimal fraction."""

    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(str(self.value)))

    @classmethod
    def from_fraction(cls, fraction: Decimal | float | int) -> Percentage:
        return cls(Decimal(str(fraction)))

    @classmethod
    def from_percentage(cls, pct: Decimal | float | int) -> Percentage:
        return cls(Decimal(str(pct)) / Decimal("100"))

    @classmethod
    def zero(cls) -> Percentage:
        return cls(Decimal("0"))

    @classmethod
    def hundred(cls) -> Percentage:
        return cls(Decimal("1"))

    def to_basis_points(self) -> Decimal:
        return self.value * Decimal("10000")

    def __add__(self, other: Percentage) -> Percentage:
        return Percentage(self.value + other.value)

    def __sub__(self, other: Percentage) -> Percentage:
        return Percentage(self.value - other.value)

    def __float__(self) -> float:
        return float(self.value * Decimal("100"))
