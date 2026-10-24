"""Tests for transaction-cost sensitivity diagnostics."""

import pandas as pd
import pytest

from ai_trading.transaction_cost_sensitivity import (
    transaction_cost_sensitivity,
    transaction_cost_summary,
)


def test_transaction_cost_sensitivity_applies_turnover_cost() -> None:
    returns = pd.Series([0.10, -0.05])
    turnover = pd.Series([1.0, 2.0])
    result = transaction_cost_sensitivity(
        returns,
        turnover=turnover,
        cost_bps=(0.0, 10.0),
    )
    assert result["cost_bps"].tolist() == [0.0, 10.0]
    assert result.loc[0, "gross_return"] == pytest.approx(0.045)
    assert result.loc[1, "net_return"] == pytest.approx(0.041852)
    assert result.loc[1, "cost_drag"] == pytest.approx(0.003148)


def test_transaction_cost_sensitivity_defaults_turnover_from_activity() -> None:
    returns = pd.Series([0.02, 0.0, -0.01])
    result = transaction_cost_sensitivity(returns, cost_bps=(10.0,))
    assert result.loc[0, "total_turnover"] == pytest.approx(2.0)


def test_transaction_cost_sensitivity_rejects_invalid_costs() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        transaction_cost_sensitivity(pd.Series([0.01]), cost_bps=(-1.0,))

    for invalid_cost in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="finite and non-negative"):
            transaction_cost_sensitivity(pd.Series([0.01]), cost_bps=(invalid_cost,))


def test_transaction_cost_sensitivity_rejects_invalid_turnover() -> None:
    returns = pd.Series([0.01, 0.02])

    for invalid_turnover in (
        pd.Series([1.0, float("nan")]),
        pd.Series([1.0, float("inf")]),
        pd.Series([1.0, -1.0]),
    ):
        with pytest.raises(ValueError, match="turnover"):
            transaction_cost_sensitivity(returns, turnover=invalid_turnover)

    with pytest.raises(ValueError, match="finite and present"):
        transaction_cost_sensitivity(
            returns,
            turnover=pd.Series([1.0], index=[0]),
        )


def test_transaction_cost_summary_reports_worst_case() -> None:
    returns = pd.Series([0.01, 0.02])
    summary = transaction_cost_summary(
        returns,
        turnover=pd.Series([1.0, 1.0]),
        cost_bps=(0.0, 20.0),
    )
    assert summary["gross_return"] == pytest.approx(0.0302)
    assert summary["worst_cost_bps"] == pytest.approx(20.0)
    assert summary["worst_net_return"] < summary["gross_return"]
