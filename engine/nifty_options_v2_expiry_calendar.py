"""Holiday-aware NIFTY Options V2 monthly expiry helpers."""

from __future__ import annotations

from datetime import date, timedelta


def monthly_expiry_for_month(year: int, month: int, holidays: set[date] | None = None) -> date:
    """Return the monthly expiry, shifting the last Thursday to the prior trading day."""
    if not 1 <= month <= 12:
        raise ValueError("month must be between 1 and 12")

    holiday_dates = holidays or set()
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)

    last_day = next_month - timedelta(days=1)
    expiry = last_day - timedelta(days=(last_day.weekday() - 3) % 7)

    while expiry in holiday_dates or expiry.weekday() >= 5:
        expiry -= timedelta(days=1)

    return expiry


def is_valid_monthly_expiry(value: date, holidays: set[date] | None = None) -> bool:
    """Return whether a date is the holiday-adjusted monthly expiry for its month."""
    return value == monthly_expiry_for_month(value.year, value.month, holidays)
