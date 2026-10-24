from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.primitives.errors import PrimitiveTypeError
from core.primitives.value_object import ValueObject


@dataclass(frozen=True, order=True)
class Percentage(ValueObject):
    """Represents a percentage value (e.g. 12.5 for 12.5%)."""

    value: Decimal

    def __init__(self, value: Decimal | int | float | str) -> None:
        try:
            dec_val = Decimal(str(value))
        except Exception as e:
            raise PrimitiveTypeError(f"Invalid percentage value: {value}") from e
        object.__setattr__(self, "value", dec_val)

    def to_fraction(self) -> Decimal:
        """Convert percentage to its fractional representation (e.g., 12.5% -> 0.125)."""
        return self.value / Decimal("100")

    @classmethod
    def from_fraction(cls, fraction: Decimal | int | float | str) -> Percentage:
        """Create a Percentage from a fractional value (e.g., 0.15 -> 15%)."""
        try:
            dec_frac = Decimal(str(fraction))
        except Exception as e:
            raise PrimitiveTypeError(f"Invalid fraction value: {fraction}") from e
        return cls(dec_frac * Decimal("100"))

    def __add__(self, other: Percentage) -> Percentage:
        if not isinstance(other, Percentage):
            return NotImplemented
        return Percentage(self.value + other.value)

    def __sub__(self, other: Percentage) -> Percentage:
        if not isinstance(other, Percentage):
            return NotImplemented
        return Percentage(self.value - other.value)

    def __mul__(self, factor: Decimal | int | float) -> Percentage:
        try:
            dec_factor = Decimal(str(factor))
        except Exception as e:
            raise PrimitiveTypeError(f"Invalid multiplication factor: {factor}") from e
        return Percentage(self.value * dec_factor)

    def to_dict(self) -> dict[str, str]:
        return {"value": str(self.value)}
