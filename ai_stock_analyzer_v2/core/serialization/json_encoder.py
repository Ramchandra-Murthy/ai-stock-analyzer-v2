from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any


class AIERPJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder handling domain primitives like Decimal, date, and dataclasses."""

    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        if hasattr(o, "to_dict") and callable(o.to_dict):
            return o.to_dict()
        return super().default(o)


def to_json(obj: Any) -> str:
    """Serialize a domain object or dictionary to a JSON string."""
    return json.dumps(obj, cls=AIERPJSONEncoder)


def from_json(json_str: str) -> Any:
    """Deserialize a JSON string."""
    return json.loads(json_str)
