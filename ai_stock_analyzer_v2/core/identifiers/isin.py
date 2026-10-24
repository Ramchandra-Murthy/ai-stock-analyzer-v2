from __future__ import annotations

from dataclasses import dataclass

from core.primitives.value_object import ValueObject


@dataclass(frozen=True, order=True)
class ISIN(ValueObject):
    """International Securities Identification Number (ISIN)."""

    code: str

    def __init__(self, code: str) -> None:
        if not code or len(code.strip()) != 12:
            raise ValueError("ISIN must be exactly 12 characters long")
        object.__setattr__(self, "code", code.strip().upper())

    def to_dict(self) -> dict[str, str]:
        return {"isin": self.code}
