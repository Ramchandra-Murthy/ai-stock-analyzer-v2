from __future__ import annotations

from core.primitives.currency import Currency


def test_currency_enums() -> None:
    assert Currency.INR == "INR"
    assert Currency.USD == "USD"
    assert Currency.EUR == "EUR"
