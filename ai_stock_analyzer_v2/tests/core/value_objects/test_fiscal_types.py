from __future__ import annotations

from datetime import date

import pytest

from core.value_objects import (
    DateRange,
    FiscalPeriod,
    FiscalQuarter,
    FiscalYear,
    QuarterEnum,
)


def test_fiscal_year() -> None:
    fy = FiscalYear(2026)
    assert fy.year == 2026
    assert str(fy) == "FY2026"
    with pytest.raises(ValueError):
        FiscalYear(1850)


def test_fiscal_quarter() -> None:
    fq = FiscalQuarter(QuarterEnum.Q1)
    assert str(fq) == "Q1"


def test_fiscal_period() -> None:
    period = FiscalPeriod.from_ints(2026, "Q3")
    assert str(period) == "FY2026-Q3"
    assert period.to_dict() == {"year": 2026, "quarter": "Q3"}


def test_date_range() -> None:
    dr = DateRange(date(2026, 4, 1), date(2026, 6, 30))
    assert dr.duration_days() == 90
    with pytest.raises(ValueError):
        DateRange(date(2026, 6, 30), date(2026, 4, 1))
