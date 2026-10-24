from datetime import date

from engine.nifty_options_v2_cycle import (
    current_and_next_monthly_expiry,
    monthly_expiries,
)


def test_monthly_expiries_selects_latest_expiry_per_month() -> None:
    expiries = (
        "2026-10-08",
        "2026-10-29",
        "2026-11-05",
        "2026-11-26",
    )

    assert monthly_expiries(expiries) == (
        date(2026, 10, 29),
        date(2026, 11, 26),
    )


def test_current_and_next_monthly_expiry_requires_two_months() -> None:
    assert current_and_next_monthly_expiry(("2026-10-29",)) is None


def test_current_and_next_monthly_expiry_returns_first_two_months() -> None:
    assert current_and_next_monthly_expiry(("2026-10-08", "2026-10-29", "2026-11-26")) == (
        date(2026, 10, 29),
        date(2026, 11, 26),
    )
