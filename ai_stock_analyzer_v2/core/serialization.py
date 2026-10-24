"""
==========================================================
CORE SERIALIZATION UTILITIES
Module  : core.serialization
Layer   : Core Infrastructure
==========================================================
"""

from __future__ import annotations

import json
from typing import Any

from core.exceptions import SerializationError


def serialize_to_json(data: dict[str, Any], indent: int = 4) -> str:
    """Serializes a dictionary payload into a formatted JSON string."""
    try:
        return json.dumps(data, indent=indent, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise SerializationError(f"Failed to serialize payload to JSON: {exc}") from exc


def deserialize_from_json(json_str: str) -> dict[str, Any]:
    """Deserializes a JSON string into a standard dictionary."""
    try:
        parsed = json.loads(json_str)
        if not isinstance(parsed, dict):
            raise SerializationError("Deserialized JSON root must be a dictionary.")
        return parsed
    except json.JSONDecodeError as exc:
        raise SerializationError(f"Failed to parse JSON string: {exc}") from exc
