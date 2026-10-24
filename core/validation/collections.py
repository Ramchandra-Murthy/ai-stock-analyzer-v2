from __future__ import annotations

from core.exceptions import ValidationError


def validate_non_empty_collection(collection: list | dict | set, field_name: str) -> None:
    if not collection:
        raise ValidationError(f"Collection '{field_name}' cannot be empty.")
