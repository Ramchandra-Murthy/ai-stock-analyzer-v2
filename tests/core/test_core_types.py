from __future__ import annotations

from decimal import Decimal

import pytest

from core.exceptions import ValidationError
from core.types import Money


def test_money_currency_mismatch() -> None:
    m_inr = Money(Decimal("100"), "INR")
    m_usd = Money(Decimal("100"), "USD")

    with pytest.raises(ValidationError, match="Cannot add different currencies"):
        _ = m_inr + m_usd
