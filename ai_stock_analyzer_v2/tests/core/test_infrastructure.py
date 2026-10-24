"""
==========================================================
CORE INFRASTRUCTURE UNIT TESTS
Module  : tests.core.test_infrastructure
Layer   : Test Automation
==========================================================
"""

from __future__ import annotations

import pytest

from core.exceptions import SerializationError, ValidationError
from core.serialization import deserialize_from_json, serialize_to_json
from core.validation import (
    validate_bounds,
    validate_finite_number,
    validate_non_empty_string,
)


def test_serialization_roundtrip() -> None:
    payload = {"ticker": "RELIANCE", "value": 2500.50}
    json_str = serialize_to_json(payload)
    assert isinstance(json_str, str)

    reconstructed = deserialize_from_json(json_str)
    assert reconstructed == payload


def test_serialization_failure() -> None:
    with pytest.raises(SerializationError):
        serialize_to_json({"invalid": {1, 2, 3}})  # type: ignore[dict-item]

    with pytest.raises(SerializationError):
        deserialize_from_json("invalid json string")


def test_validation_helpers() -> None:
    validate_non_empty_string("TCS", "ticker")
    with pytest.raises(ValidationError):
        validate_non_empty_string("   ", "ticker")

    validate_finite_number(100.25, "price")
    with pytest.raises(ValidationError):
        validate_finite_number(float("nan"), "price")

    validate_bounds(0.15, 0.0, 1.0, "tax_rate")
    with pytest.raises(ValidationError):
        validate_bounds(1.5, 0.0, 1.0, "tax_rate")
