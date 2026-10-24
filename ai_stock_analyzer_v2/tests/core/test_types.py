from __future__ import annotations

import pytest

from core.exceptions import ValidationError
from core.types import Currency, FiscalPeriod, Money


def test_currency_validation() -> None:
    curr = Currency("inr")
    assert curr.code == "INR"
    with pytest.raises(ValidationError):
        Currency("invalid")


def test_money_operations() -> None:
    m1 = Money(100.50, "INR")
    m2 = Money(50.25, "INR")
    m3 = m1 + m2
    assert float(m3.amount) == 150.75
    assert str(m3.currency) == "INR"

    with pytest.raises(ValidationError):
        _ = m1 + Money(10.0, "USD")


def test_fiscal_period() -> None:
    fp_year = FiscalPeriod(2026)
    assert str(fp_year) == "FY2026"

    fp_qtr = FiscalPeriod(2026, 2)
    assert str(fp_qtr) == "FY2026-Q2"

    with pytest.raises(ValidationError):
        FiscalPeriod(1800)
