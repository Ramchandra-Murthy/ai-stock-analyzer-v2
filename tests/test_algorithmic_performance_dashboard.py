import pandas as pd
import pytest

from algorithmic_trading.performance_feedback import (
    drawdown_curve,
    equity_curve,
    summarize_performance,
)


def test_performance_dashboard_inputs_are_compatible():
    trades = pd.DataFrame({"pnl": [100.0, -50.0, 25.0]})
    summary = summarize_performance(trades)

    assert summary.trades == 3
    assert summary.total_pnl == pytest.approx(75.0)
    assert summary.profit_factor == pytest.approx(2.5)


def test_dashboard_equity_and_drawdown_are_consistent():
    trades = pd.DataFrame({"pnl": [100.0, -150.0, 200.0]})
    equity = equity_curve(trades, initial_capital=10_000.0)
    drawdown = drawdown_curve(equity)

    assert equity.iloc[-1] == pytest.approx(10_150.0)
    assert drawdown.min() < 0
    assert drawdown.iloc[-1] == pytest.approx(0.0)
