from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.primitives.currency import Currency
from core.primitives.errors import CurrencyMismatchError, PrimitiveTypeError
from core.primitives.value_object import ValueObject


@dataclass(frozen=True, order=True)
class Money(ValueObject):
    """Represents a monetary amount with a specific currency."""

    amount: Decimal
    currency: Currency

    def __init__(self, amount: Decimal | int | float | str, currency: Currency | str) -> None:
        if isinstance(currency, str):
            curr = Currency(currency)
        elif isinstance(currency, Currency):
            curr = currency
        else:
            raise PrimitiveTypeError("Invalid currency type provided.")

        try:
            dec_amount = Decimal(str(amount))
        except Exception as e:
            raise PrimitiveTypeError(f"Invalid amount for Money: {amount}") from e

        object.__setattr__(self, "amount", dec_amount.quantize(Decimal("0.01")))
        object.__setattr__(self, "currency", curr)

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise CurrencyMismatchError(
                f"Cannot add currencies {self.currency.code} and {other.currency.code}"
            )
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise CurrencyMismatchError(
                f"Cannot subtract currencies {self.currency.code} and {other.currency.code}"
            )
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: Decimal | int | float) -> Money:
        try:
            dec_factor = Decimal(str(factor))
        except Exception as e:
            raise PrimitiveTypeError(f"Invalid multiplier factor: {factor}") from e
        return Money(self.amount * dec_factor, self.currency)

    def __truediv__(self, divisor: Decimal | int | float) -> Money:
        try:
            dec_divisor = Decimal(str(divisor))
        except Exception as e:
            raise PrimitiveTypeError(f"Invalid divisor: {divisor}") from e
        if dec_divisor == 0:
            raise ZeroDivisionError("Division by zero in Money amount.")
        return Money(self.amount / dec_divisor, self.currency)

    def to_dict(self) -> dict[str, str]:
        return {
            "amount": str(self.amount),
            "currency": self.currency.code,
        }
