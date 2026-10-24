from __future__ import annotations

from dataclasses import dataclass

from core.primitives.errors import PrimitiveTypeError
from core.primitives.value_object import ValueObject


@dataclass(frozen=True, order=True)
class Currency(ValueObject):
    """Represents an ISO 4217 currency code with convenient class-level constants and string equality support."""

    code: str

    def __init__(self, code: str) -> None:
        if not code or not isinstance(code, str) or len(code.strip()) != 3:
            raise PrimitiveTypeError("Currency code must be a valid 3-letter ISO string.")
        object.__setattr__(self, "code", code.strip().upper())

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Currency):
            return self.code == other.code
        if isinstance(other, str):
            return self.code == other.strip().upper()
        return False

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code}


# Common currency class-level attributes
Currency.INR = Currency("INR")
Currency.USD = Currency("USD")
Currency.EUR = Currency("EUR")
Currency.GBP = Currency("GBP")
