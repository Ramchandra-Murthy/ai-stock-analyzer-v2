from datetime import date

from strategy.nifty_options_v2_expiry import last_thursday, monthly_expiry


def test_last_thursday_returns_last_thursday_of_month() -> None:
    assert last_thursday(2021, 5) == date(2021, 5, 27)


def test_monthly_expiry_shifts_previous_day_for_supplied_holiday() -> None:
    thursday = date(2021, 5, 27)
    assert monthly_expiry(2021, 5, {thursday}) == date(2021, 5, 26)


def test_monthly_expiry_does_not_assume_exchange_holidays() -> None:
    assert monthly_expiry(2021, 5) == date(2021, 5, 27)
