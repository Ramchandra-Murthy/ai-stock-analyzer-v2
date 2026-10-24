from __future__ import annotations

from functools import total_ordering
from typing import Any


class SerializableMixin:
    """Provides standard serialization hooks for primitive value objects."""

    def to_dict(self) -> dict[str, Any]:
        """Convert the value object into a serializable dictionary."""
        raise NotImplementedError("Subclasses must implement to_dict().")


@total_ordering
class ComparableMixin:
    """Provides consistent ordering and equality for numeric value objects."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._get_comparison_value() == other._get_comparison_value()

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._get_comparison_value() < other._get_comparison_value()

    def _get_comparison_value(self) -> Any:
        raise NotImplementedError
