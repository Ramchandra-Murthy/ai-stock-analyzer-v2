from __future__ import annotations

import math

from core.exceptions import ValidationError


def validate_non_empty_string(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f'Field "{field_name}" must be a non-empty string.')


def validate_finite_number(value: float, field_name: str) -> None:
    if math.isnan(value) or math.isinf(value):
        raise ValidationError(f'Field "{field_name}" must be a finite number, got: {value}')


def validate_bounds(value: float, lower: float, upper: float, field_name: str) -> None:
    validate_finite_number(value, field_name)
    if not (lower <= value <= upper):
        raise ValidationError(
            f'Field "{field_name}" value {value} is out of bounds [{lower}, {upper}].'
        )
