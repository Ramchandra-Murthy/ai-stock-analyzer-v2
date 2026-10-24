from __future__ import annotations

from decimal import Decimal

from core.primitives.percentage import Percentage


def test_percentage_fraction_conversion() -> None:
    p = Percentage("12.5")
    assert p.value == Decimal("12.5000")
    assert p.to_fraction() == Decimal("0.125000")

    p2 = Percentage.from_fraction("0.15")
    assert p2.value == Decimal("15.0000")


def test_percentage_arithmetic() -> None:
    p1 = Percentage("10")
    p2 = Percentage("5")
    assert (p1 + p2).value == Decimal("15.0000")
    assert (p1 - p2).value == Decimal("5.0000")
    assert (p1 * 2).value == Decimal("20.0000")
