from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.primitives.base import ValueObject


@dataclass(frozen=True, order=True)
class Sector(ValueObject):
    """Market sector classification (e.g., Information Technology, Financials)."""

    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Sector name cannot be empty.")
        object.__setattr__(self, "name", self.name.strip().title())

    def __str__(self) -> str:
        return self.name

    def to_dict(self) -> dict[str, Any]:
        return {"sector": self.name}


@dataclass(frozen=True, order=True)
class Industry(ValueObject):
    """Specific industry classification within a sector."""

    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Industry name cannot be empty.")
        object.__setattr__(self, "name", self.name.strip().title())

    def __str__(self) -> str:
        return self.name

    def to_dict(self) -> dict[str, Any]:
        return {"industry": self.name}
