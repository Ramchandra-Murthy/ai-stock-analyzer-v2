import pandas as pd
import pytest

from algorithmic_trading.performance_feedback import (
    drawdown_curve,
    equity_curve,
    group_performance,
    summarize_performance,
)


def sample_trades() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": ["RELIANCE", "TCS", "RELIANCE", "TCS"],
            "signal": ["LONG", "SHORT", "LONG", "SHORT"],
            "regime": ["TREND", "RANGE", "TREND", "TREND"],
            "pnl": [1000.0, -400.0, -200.0, 600.0],
        }
    )


def test_summary_and_profit_factor():
    summary = summarize_performance(sample_trades())

    assert summary.trades == 4
    assert summary.wins == 2
    assert summary.losses == 2
    assert summary.win_rate == pytest.approx(0.5)
    assert summary.total_pnl == pytest.approx(1000.0)
    assert summary.profit_factor == pytest.approx(1600.0 / 600.0)


def test_group_performance_is_auditable():
    result = group_performance(sample_trades(), "symbol")

    reliance = result.loc[result["symbol"] == "RELIANCE"].iloc[0]
    assert reliance["trades"] == 2
    assert reliance["total_pnl"] == pytest.approx(800.0)


def test_equity_and_drawdown():
    equity = equity_curve(sample_trades(), initial_capital=100_000.0)
    drawdown = drawdown_curve(equity)

    assert equity.iloc[-1] == pytest.approx(101_000.0)
    assert drawdown.iloc[2] < 0
    assert drawdown.iloc[-1] == pytest.approx(0.0)


def test_missing_pnl_is_rejected():
    with pytest.raises(ValueError, match="pnl"):
        summarize_performance(pd.DataFrame({"symbol": ["TCS"]}))
