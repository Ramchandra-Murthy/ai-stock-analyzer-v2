from __future__ import annotations

from decimal import Decimal

import pytest

from core.primitives.currency import Currency
from core.primitives.errors import CurrencyMismatchError
from core.primitives.money import Money


def test_money_creation() -> None:
    m = Money("1000.506", Currency.INR)
    assert m.amount == Decimal("1000.51")
    assert m.currency.code == "INR"


def test_money_arithmetic() -> None:
    m1 = Money("100.00", Currency.USD)
    m2 = Money("50.00", Currency.USD)
    assert (m1 + m2).amount == Decimal("150.00")
    assert (m1 - m2).amount == Decimal("50.00")
    assert (m1 * 2).amount == Decimal("200.00")
    assert (m1 / 2).amount == Decimal("50.00")


def test_money_currency_mismatch() -> None:
    m_inr = Money("100", Currency.INR)
    m_usd = Money("100", Currency.USD)
    with pytest.raises(CurrencyMismatchError):
        _ = m_inr + m_usd


def test_money_serialization() -> None:
    m = Money("500.25", Currency.EUR)
    d = m.to_dict()
    assert d["amount"] == "500.25"
    assert d["currency"] == "EUR"
