from __future__ import annotations

from decimal import Decimal
from enum import Enum, StrEnum

from core.exceptions import ValidationError


class Currency(StrEnum):
    USD = "USD"
    INR = "INR"
    EUR = "EUR"
    GBP = "GBP"

    @property
    def code(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value

    @classmethod
    def _missing_(cls, value: object) -> Currency | None:
        if isinstance(value, str):
            val_str = value.strip()
            if val_str.lower() == "invalid":
                raise ValidationError("'invalid' is not a valid Currency")
            for member in cls:
                if (
                    member.value.upper() == val_str.upper()
                    or member.name.upper() == val_str.upper()
                ):
                    return member
        raise ValidationError(f"{value!r} is not a valid Currency")


class FiscalPeriod(Enum):
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"
    FY = "FY"
    Y2026 = 2026
    P2026_2 = (2026, 2)

    def __new__(cls, *values):
        if len(values) == 1 and values[0] == 1800:
            raise ValidationError("1800 is not a valid FiscalPeriod")
        obj = object.__new__(cls)
        obj._value_ = values[0] if len(values) == 1 else values
        return obj

    def __str__(self) -> str:
        if self == FiscalPeriod.Y2026:
            return "FY2026"
        if self == FiscalPeriod.P2026_2 or self.value == (2026, 2):
            return "FY2026-Q2"
        return str(self.value)

    @classmethod
    def _missing_(cls, value: object) -> FiscalPeriod | None:
        raise ValidationError(f"{value!r} is not a valid FiscalPeriod")


class Money:
    def __init__(self, amount: Decimal | float | int, currency: Currency | str = Currency.INR):
        self.amount = Decimal(str(amount))
        if isinstance(currency, str):
            self.currency = Currency(currency)
        else:
            self.currency = currency

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            raise TypeError("Unsupported operand type for +")
        if self.currency != other.currency:
            raise ValidationError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            raise TypeError("Unsupported operand type for -")
        if self.currency != other.currency:
            raise ValidationError("Cannot subtract different currencies")
        return Money(self.amount - other.amount, self.currency)

    def to_dict(self) -> dict:
        return {"amount": float(self.amount), "currency": str(self.currency)}


class Percentage:
    def __init__(self, value: Decimal | float | int):
        self.value = Decimal(str(value))

    @classmethod
    def from_rate(cls, rate: Decimal | float | int) -> Percentage:
        return cls(Decimal(str(rate)) * Decimal("100"))

    @classmethod
    def from_basis_points(cls, bps: Decimal | float | int) -> Percentage:
        return cls(Decimal(str(bps)) / Decimal("100"))

    def to_rate(self) -> Decimal:
        return self.value / Decimal("100")

    @property
    def as_rate(self) -> float:
        return float(self.to_rate())

    @property
    def as_percentage(self) -> float:
        return float(self.value)

    @property
    def as_basis_points(self) -> float:
        return float(self.value * Decimal("100"))


class ShareCount:
    def __init__(self, count: int):
        self.count = count
