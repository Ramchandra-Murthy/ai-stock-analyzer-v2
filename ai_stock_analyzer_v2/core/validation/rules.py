"""Compatibility validators for legacy domain imports."""

from __future__ import annotations

from core.validation.numbers import validate_finite_number, validate_positive
from core.validation.strings import validate_non_empty_string


class StringValidators:
    """Legacy string validation facade."""

    @staticmethod
    def non_empty(value: str, field_name: str = "Value") -> str:
        validate_non_empty_string(value, field_name)
        return value


class NumericValidators:
    """Legacy numeric validation facade."""

    @staticmethod
    def non_negative(value: float, field_name: str = "Value") -> float:
        number = float(value)
        validate_finite_number(number, field_name)
        if number < 0:
            raise ValueError(f"{field_name} must be non-negative")
        return number

    @staticmethod
    def positive(value: float, field_name: str = "Value") -> float:
        number = float(value)
        validate_positive(number, field_name)
        return number
