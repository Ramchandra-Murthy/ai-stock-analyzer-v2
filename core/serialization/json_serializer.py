from __future__ import annotations

import json
from decimal import Decimal
from enum import StrEnum
from typing import Any


class DomainJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder handling Decimals, StrEnums, and ValueObjects."""

    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, StrEnum):
            return o.value
        if hasattr(o, "to_dict") and callable(o.to_dict):
            return o.to_dict()
        return super().default(o)


class JsonSerializer:
    @staticmethod
    def serialize(obj: Any) -> str:
        return json.dumps(obj, cls=DomainJSONEncoder, indent=2)

    @staticmethod
    def deserialize(payload: str) -> dict[str, Any]:
        return json.loads(payload)
