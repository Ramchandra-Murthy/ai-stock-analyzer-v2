from __future__ import annotations

import math

from core.exceptions import ValidationError


def validate_finite_number(value: float | int, field_name: str) -> None:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValidationError(f"Field '{field_name}' must be a finite number, got: {value}")


def validate_bounds(
    value: float | int, lower: float | int, upper: float | int, field_name: str
) -> None:
    validate_finite_number(value, field_name)
    if not (lower <= value <= upper):
        raise ValidationError(
            f"Field '{field_name}' value {value} is out of bounds [{lower}, {upper}]."
        )


def validate_positive(value: float | int, field_name: str) -> None:
    validate_finite_number(value, field_name)
    if value <= 0:
        raise ValidationError(f"Field '{field_name}' must be strictly positive, got: {value}")
