from __future__ import annotations

import json
from decimal import Decimal
from json import JSONDecodeError
from typing import Any

from core.exceptions import SerializationError


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, set):
            raise SerializationError("Object of type set is not JSON serializable")
        if hasattr(o, "to_dict") and callable(o.to_dict):
            return o.to_dict()
        if hasattr(o, "__dict__"):
            return o.__dict__
        raise SerializationError(f"Object of type {o.__class__.__name__} is not JSON serializable")


class JsonSerializer:
    @staticmethod
    def serialize(obj: Any) -> str:
        try:
            return json.dumps(obj, cls=CustomJSONEncoder)
        except Exception as e:
            if isinstance(e, SerializationError):
                raise
            raise SerializationError(str(e)) from e

    @staticmethod
    def deserialize(s: str) -> Any:
        try:
            return json.loads(s)
        except Exception as e:
            if isinstance(e, (JSONDecodeError, SerializationError)):
                raise SerializationError(str(e)) from e
            raise SerializationError(str(e)) from e


def serialize_to_json(obj: Any) -> str:
    return JsonSerializer.serialize(obj)


def deserialize_from_json(s: str) -> Any:
    return JsonSerializer.deserialize(s)


def to_json(obj: Any) -> str:
    return JsonSerializer.serialize(obj)


def from_json(s: str) -> Any:
    return JsonSerializer.deserialize(s)
