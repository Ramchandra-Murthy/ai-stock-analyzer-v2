from __future__ import annotations

from decimal import Decimal

import pytest

from core.exceptions import ValidationError
from forecast.domain import FinancialProjection


def test_financial_projection_creation() -> None:
    proj = FinancialProjection(
        period_label="FY2027",
        projected_revenue=Decimal("1000000.00"),
        projected_ebitda=Decimal("250000.00"),
        confidence_score=Decimal("0.85"),
    )
    assert proj.period_label == "FY2027"
    assert proj.ebitda_margin() == Decimal("25.0")


def test_financial_projection_validation() -> None:
    with pytest.raises((ValidationError, ValueError)):
        FinancialProjection(
            period_label="FY2027",
            projected_revenue=Decimal("-100"),
            projected_ebitda=Decimal("50"),
            confidence_score=Decimal("0.5"),
        )
