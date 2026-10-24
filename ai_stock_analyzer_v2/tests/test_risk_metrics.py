"""Tests for book-aligned EROS risk and performance metrics."""

import pandas as pd
import pytest

from ai_trading.risk_metrics import (
    annualized_volatility,
    conditional_value_at_risk,
    max_drawdown,
    omega_ratio,
    risk_performance_summary,
    sharpe_ratio,
)


def test_annualized_volatility_and_sharpe_are_positive_for_positive_returns() -> None:
    returns = pd.Series([0.01, 0.02, -0.005, 0.015, 0.01])
    assert annualized_volatility(returns) > 0.0
    assert sharpe_ratio(returns) > 0.0


def test_max_drawdown_matches_equity_path() -> None:
    returns = pd.Series([0.10, -0.05, -0.10, 0.02])
    expected = 1.0 - (1.10 * 0.95 * 0.90) / 1.10
    assert max_drawdown(returns) == pytest.approx(expected)


def test_omega_ratio_uses_positive_and_negative_excess_returns() -> None:
    returns = pd.Series([0.02, -0.02, 0.03, -0.03])
    assert omega_ratio(returns) == pytest.approx(1.0)


def test_cvar_is_tail_loss_magnitude() -> None:
    returns = pd.Series([0.02, 0.01, -0.01, -0.04, -0.08])
    assert conditional_value_at_risk(returns, confidence=0.8) > 0.04


def test_summary_contains_composite_metrics() -> None:
    summary = risk_performance_summary(pd.Series([0.01, -0.005, 0.02, -0.01]))
    assert set(summary) == {
        "annualized_volatility",
        "sharpe_ratio",
        "omega_ratio",
        "conditional_value_at_risk",
        "max_drawdown",
    }


def test_invalid_parameters_are_rejected() -> None:
    with pytest.raises(ValueError):
        annualized_volatility(pd.Series([0.01, 0.02]), periods_per_year=0)
    with pytest.raises(ValueError):
        conditional_value_at_risk(pd.Series([0.01, 0.02]), confidence=1.0)
