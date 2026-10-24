from __future__ import annotations

from core.validation.numbers import validate_bounds, validate_positive


def validate_percentage(value: float, field_name: str = "percentage") -> None:
    validate_bounds(value, 0.0, 1.0, field_name)


def validate_monetary_amount(amount: float, field_name: str = "amount") -> None:
    validate_positive(amount, field_name)
