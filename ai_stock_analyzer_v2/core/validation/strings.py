from __future__ import annotations

from core.exceptions import ValidationError


def validate_non_empty_string(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Field '{field_name}' must be a non-empty string.")
