from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.primitives.errors import PrimitiveTypeError
from core.primitives.value_object import ValueObject


@dataclass(frozen=True, order=True)
class Quantity(ValueObject):
    """Represents a numerical quantity or count of shares/units."""

    value: Decimal

    def __init__(self, value: Decimal | int | float | str) -> None:
        try:
            dec_val = Decimal(str(value))
        except Exception as e:
            raise PrimitiveTypeError(f"Invalid quantity value: {value}") from e
        object.__setattr__(self, "value", dec_val)

    def __add__(self, other: Quantity) -> Quantity:
        if not isinstance(other, Quantity):
            return NotImplemented
        return Quantity(self.value + other.value)

    def __sub__(self, other: Quantity) -> Quantity:
        if not isinstance(other, Quantity):
            return NotImplemented
        return Quantity(self.value - other.value)

    def __mul__(self, factor: Decimal | int | float) -> Quantity:
        try:
            dec_factor = Decimal(str(factor))
        except Exception as e:
            raise PrimitiveTypeError(f"Invalid multiplication factor: {factor}") from e
        return Quantity(self.value * dec_factor)

    def to_dict(self) -> dict[str, str]:
        return {"value": str(self.value)}
