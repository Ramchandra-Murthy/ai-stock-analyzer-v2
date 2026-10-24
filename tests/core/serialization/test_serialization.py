from __future__ import annotations

from decimal import Decimal

from core.primitives import Currency, Money
from core.serialization import JsonSerializer


def test_json_serialization() -> None:
    money = Money(Decimal("1250.75"), Currency.INR)
    payload = JsonSerializer.serialize(money)
    assert "1250.75" in payload
    assert "INR" in payload
