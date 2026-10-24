from __future__ import annotations

import pytest

from core.exceptions import (
    AIERPError,
    CalculationError,
    DomainError,
    InfrastructureError,
    SerializationError,
    ValidationError,
)


def test_exception_hierarchy() -> None:
    assert issubclass(DomainError, AIERPError)
    assert issubclass(CalculationError, DomainError)
    assert issubclass(ValidationError, DomainError)
    assert issubclass(SerializationError, AIERPError)
    assert issubclass(InfrastructureError, AIERPError)


def test_raising_exceptions() -> None:
    with pytest.raises(ValidationError):
        raise ValidationError("Invalid input parameter")

    with pytest.raises(CalculationError):
        raise CalculationError("Calculation diverged")
