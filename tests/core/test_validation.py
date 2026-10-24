from __future__ import annotations

import pytest

from core.exceptions import ValidationError
from core.validation import validate_percentage


def test_finance_validation() -> None:
    validate_percentage(25.0, "rate")
    with pytest.raises(ValidationError):
        validate_percentage(150.0, "rate")
