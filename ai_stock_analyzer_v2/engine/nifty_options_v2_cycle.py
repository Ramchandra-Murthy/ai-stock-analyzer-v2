"""Monthly cycle helpers for NIFTY Options V2 paper trading."""

from __future__ import annotations

from datetime import date


def monthly_expiries(expiries: tuple[str, ...]) -> tuple[date, ...]:
    """Return one provider-reported expiry per month, using the latest date."""
    parsed = sorted({date.fromisoformat(value) for value in expiries})
    by_month: dict[tuple[int, int], date] = {}

    for expiry in parsed:
        key = (expiry.year, expiry.month)
        by_month[key] = max(by_month.get(key, expiry), expiry)

    return tuple(sorted(by_month.values()))


def current_and_next_monthly_expiry(
    expiries: tuple[str, ...],
) -> tuple[date, date] | None:
    """Return the first two provider-reported monthly expiries when available."""
    values = monthly_expiries(expiries)
    if len(values) < 2:
        return None
    return values[0], values[1]
