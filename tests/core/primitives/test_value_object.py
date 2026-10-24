from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest

from core.primitives import ValueObject


@dataclass(frozen=True)
class DummyValue(ValueObject):
    amount: Decimal
    label: str


def test_value_object_immutability() -> None:
    obj = DummyValue(Decimal("100.00"), "Test")
    assert obj.amount == Decimal("100.00")
    assert obj.label == "Test"

    with pytest.raises(Exception):
        obj.label = "Changed"  # type: ignore


def test_value_object_equality() -> None:
    obj1 = DummyValue(Decimal("100.00"), "Test")
    obj2 = DummyValue(Decimal("100.00"), "Test")
    obj3 = DummyValue(Decimal("200.00"), "Test")

    assert obj1 == obj2
    assert obj1 != obj3
    assert hash(obj1) == hash(obj2)


def test_value_object_serialization() -> None:
    obj = DummyValue(Decimal("150.50"), "Revenue")
    d = obj.to_dict()
    assert d == {"amount": Decimal("150.50"), "label": "Revenue"}

    j = obj.to_json()
    assert "150.50" in j
    assert "Revenue" in j
