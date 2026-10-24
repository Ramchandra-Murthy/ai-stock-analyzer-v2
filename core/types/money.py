from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from core.types.currency import Currency


@dataclass(frozen=True, order=True)
class Money:
    """Immutable representation of monetary value with currency context."""

    amount: Decimal
    currency: Currency = Currency.INR

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        if isinstance(self.currency, str):
            object.__setattr__(self, "currency", Currency(self.currency.upper()))

    def __add__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot add different currencies: {self.currency} and {other.currency}"
            )
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot subtract different currencies: {self.currency} and {other.currency}"
            )
        return Money(self.amount - other.amount, self.currency)

    def to_dict(self) -> dict[str, Any]:
        return {"amount": str(self.amount), "currency": str(self.currency)}
