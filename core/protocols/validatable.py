from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Validatable(Protocol):
    """Protocol for objects that implement explicit self-validation."""

    def validate(self) -> None: ...
