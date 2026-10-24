from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from core.primitives.base import ValueObject


@dataclass(frozen=True)
class DateRange(ValueObject):
    """Immutable representation of a calendar or fiscal date interval."""

    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if not isinstance(self.start_date, date) or not isinstance(self.end_date, date):
            raise TypeError("DateRange boundaries must be valid datetime.date instances.")
        if self.start_date > self.end_date:
            raise ValueError(
                f"Start date {self.start_date} cannot be after end date {self.end_date}."
            )

    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "duration_days": self.duration_days(),
        }
