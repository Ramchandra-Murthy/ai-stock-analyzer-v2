from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class ShareCount:
    """Immutable representation of outstanding share counts."""

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int):
            object.__setattr__(self, "value", int(self.value))
        if self.value < 0:
            raise ValueError("Share count cannot be negative.")

    def __add__(self, other: ShareCount) -> ShareCount:
        return ShareCount(self.value + other.value)

    def __sub__(self, other: ShareCount) -> ShareCount:
        return ShareCount(self.value - other.value)
