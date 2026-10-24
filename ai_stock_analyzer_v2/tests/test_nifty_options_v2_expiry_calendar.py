from datetime import date

from engine.nifty_options_v2_expiry_calendar import (
    is_valid_monthly_expiry,
    monthly_expiry_for_month,
)


def test_monthly_expiry_is_last_thursday_when_not_holiday() -> None:
    assert monthly_expiry_for_month(2026, 10) == date(2026, 10, 29)


def test_monthly_expiry_shifts_to_previous_trading_day_for_holiday() -> None:
    holidays = {date(2026, 10, 29)}
    assert monthly_expiry_for_month(2026, 10, holidays) == date(2026, 10, 28)


def test_monthly_expiry_skips_weekend_when_shifted() -> None:
    holidays = {date(2026, 10, 29), date(2026, 10, 28)}
    assert monthly_expiry_for_month(2026, 10, holidays) == date(2026, 10, 27)


def test_is_valid_monthly_expiry_uses_holiday_adjustment() -> None:
    holidays = {date(2026, 10, 29)}
    assert is_valid_monthly_expiry(date(2026, 10, 28), holidays)
    assert not is_valid_monthly_expiry(date(2026, 10, 29), holidays)
