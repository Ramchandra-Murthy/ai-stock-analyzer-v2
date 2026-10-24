from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ValueObjectProtocol(Protocol):
    """Protocol defining the required characteristics of a domain value object."""

    def to_dict(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ValueObject:
    """Base class for all immutable domain value objects.

    Provides standard immutability, hashing, and serialization hooks.
    """

    def to_dict(self) -> dict[str, Any]:
        """Convert value object to a primitive dictionary for serialization."""
        raise NotImplementedError
