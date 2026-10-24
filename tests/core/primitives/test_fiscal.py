from __future__ import annotations

import pytest

from core.primitives.fiscal import FiscalPeriod, Frequency


def test_fiscal_period_annual() -> None:
    fp = FiscalPeriod(year=2025, frequency=Frequency.ANNUAL)
    assert fp.year == 2025
    assert fp.frequency == Frequency.ANNUAL
    assert fp.to_dict()["year"] == 2025


def test_fiscal_period_quarterly() -> None:
    fp = FiscalPeriod(year=2026, quarter=3, frequency=Frequency.QUARTERLY)
    assert fp.quarter == 3
    assert fp.frequency == Frequency.QUARTERLY


def test_fiscal_period_invalid_quarter() -> None:
    with pytest.raises(ValueError):
        FiscalPeriod(year=2026, quarter=5, frequency=Frequency.QUARTERLY)
