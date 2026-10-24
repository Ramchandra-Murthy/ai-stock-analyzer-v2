from __future__ import annotations

from dataclasses import dataclass

from core.primitives.value_object import ValueObject


@dataclass(frozen=True, order=True)
class CompanySymbol(ValueObject):
    """Company symbol identifier."""

    value: str

    def __init__(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("Company symbol cannot be empty")
        object.__setattr__(self, "value", value.strip().upper())

    def to_dict(self) -> dict[str, str]:
        return {"symbol": self.value}
