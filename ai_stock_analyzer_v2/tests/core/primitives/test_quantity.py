from __future__ import annotations

from decimal import Decimal

from core.primitives.quantity import Quantity


def test_quantity_operations() -> None:
    q1 = Quantity("1000")
    q2 = Quantity("500")
    assert (q1 + q2).value == Decimal("1500.0000")
    assert (q1 * 3).value == Decimal("3000.0000")
