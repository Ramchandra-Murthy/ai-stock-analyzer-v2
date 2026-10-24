"""Tests for AI paper-trading risk controls."""

import pytest

from ai_trading.risk import RiskLimits, risk_warnings


def test_allocation_respects_exposure_position_and_cash_limits() -> None:
    limits = RiskLimits(
        max_exposure_pct=80.0,
        max_position_pct=20.0,
        cash_reserve_pct=10.0,
    )

    allocation = limits.allocation(
        equity=100_000.0,
        cash=70_000.0,
        market_value=30_000.0,
        candidate_count=4,
    )

    assert allocation["total_available"] == pytest.approx(50_000.0)
    assert allocation["per_candidate"] == pytest.approx(20_000.0)
    assert allocation["reserve_value"] == pytest.approx(10_000.0)


def test_allocation_is_zero_when_exposure_limit_is_reached() -> None:
    limits = RiskLimits(max_exposure_pct=80.0, max_position_pct=20.0)

    allocation = limits.allocation(
        equity=100_000.0,
        cash=20_000.0,
        market_value=80_000.0,
        candidate_count=2,
    )

    assert allocation["total_available"] == 0.0
    assert allocation["per_candidate"] == 0.0


def test_invalid_position_limit_is_rejected() -> None:
    with pytest.raises(ValueError, match="max_position_pct"):
        RiskLimits(max_exposure_pct=40.0, max_position_pct=50.0)


def test_risk_warnings_report_excess_exposure_and_low_reserve() -> None:
    limits = RiskLimits(max_exposure_pct=80.0, cash_reserve_pct=20.0)

    warnings = risk_warnings(
        equity=100_000.0,
        cash=10_000.0,
        market_value=90_000.0,
        limits=limits,
    )

    assert len(warnings) == 2
