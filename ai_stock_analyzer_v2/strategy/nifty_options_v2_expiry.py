"""Monthly expiry helpers for the NIFTY Options Book V2 methodology."""

from __future__ import annotations

import calendar
from datetime import date, timedelta


def last_thursday(year: int, month: int) -> date:
    """Return the last Thursday of a calendar month."""
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    return last_day - timedelta(days=(last_day.weekday() - 3) % 7)


def monthly_expiry(year: int, month: int, holidays: set[date] | None = None) -> date:
    """Return the last-Thursday expiry, shifted to the prior working day if needed.

    The caller supplies the holiday set because this module does not embed an
    exchange holiday calendar.
    """
    expiry = last_thursday(year, month)
    holiday_set = holidays or set()
    while expiry in holiday_set or expiry.weekday() >= 5:
        expiry -= timedelta(days=1)
    return expiry
