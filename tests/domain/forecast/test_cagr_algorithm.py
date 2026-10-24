from __future__ import annotations

from decimal import Decimal

import pytest

from domain.forecast.algorithms.cagr import CAGRCalculator


def test_cagr_calculation() -> None:
    history = (Decimal("100"), Decimal("110"), Decimal("121"))
    projections = CAGRCalculator.calculate(history, periods_to_forecast=2)

    # 100 to 121 over 2 periods is 10% CAGR.
    # Next 2 periods: 121 * 1.10 = 133.10, 133.10 * 1.10 = 146.41
    assert projections[0] == Decimal("133.10")
    assert projections[1] == Decimal("146.41")


def test_cagr_invalid_history() -> None:
    with pytest.raises(ValueError):
        CAGRCalculator.calculate((Decimal("100"),), periods_to_forecast=1)
