"""Tests for AI paper-trading performance analytics."""

from datetime import UTC, datetime, timedelta

import pytest

from ai_trading.paper_trading import EquitySnapshot, PaperPortfolio
from ai_trading.performance import build_equity_curve, build_performance_report


def test_performance_report_tracks_realized_and_unrealized_pnl() -> None:
    portfolio = PaperPortfolio(initial_cash=100_000.0)
    portfolio.execute("RELIANCE", "BUY", 10, 2_000.0)
    portfolio.execute("RELIANCE", "SELL", 5, 2_200.0)

    report = build_performance_report(
        portfolio.initial_cash,
        portfolio.trades,
        portfolio.positions,
        {"RELIANCE": 2_000.0},
        {"RELIANCE": 2_300.0},
        portfolio.equity({"RELIANCE": 2_300.0}),
    )

    assert report.realized_pnl == pytest.approx(1_000.0)
    assert report.unrealized_pnl == pytest.approx(1_500.0)
    assert report.total_pnl == pytest.approx(2_500.0)
    assert report.winning_trades == 1
    assert report.win_rate_pct == pytest.approx(100.0)
    assert report.trade_count == 2


def test_performance_report_calculates_drawdown_and_profit_factor() -> None:
    portfolio = PaperPortfolio(initial_cash=100_000.0)
    portfolio.execute("A", "BUY", 10, 100.0)
    portfolio.execute("A", "SELL", 10, 120.0)
    portfolio.execute("B", "BUY", 10, 100.0)
    portfolio.execute("B", "SELL", 10, 90.0)

    report = build_performance_report(
        portfolio.initial_cash,
        portfolio.trades,
        portfolio.positions,
        {},
        {},
        portfolio.equity({}),
    )

    assert report.realized_pnl == pytest.approx(100.0)
    assert report.winning_trades == 1
    assert report.losing_trades == 1
    assert report.win_rate_pct == pytest.approx(50.0)
    assert report.profit_factor == pytest.approx(2.0)
    assert report.max_drawdown_pct > 0


def test_equity_curve_tracks_returns_and_drawdown() -> None:
    start = datetime(2026, 10, 1, tzinfo=UTC)
    curve = build_equity_curve(
        [
            EquitySnapshot(start, 100_000.0),
            EquitySnapshot(start + timedelta(minutes=1), 102_000.0),
            EquitySnapshot(start + timedelta(minutes=2), 99_000.0),
        ]
    )

    assert curve["return_pct"].iloc[-1] == pytest.approx(-1.0)
    assert curve["drawdown_pct"].iloc[-1] == pytest.approx(2.941176, rel=1e-5)
    assert curve["drawdown_pct"].max() == pytest.approx(2.941176, rel=1e-5)


def test_equity_curve_is_empty_without_snapshots() -> None:
    curve = build_equity_curve([])
    assert curve.empty
    assert list(curve.columns) == ["timestamp", "equity", "return_pct", "drawdown_pct"]


def test_partial_sell_counts_one_trade_using_aggregate_realized_pnl() -> None:
    portfolio = PaperPortfolio(initial_cash=10_000.0)
    portfolio.execute("A", "BUY", 5, 100.0)
    portfolio.execute("A", "BUY", 5, 200.0)
    portfolio.execute("A", "SELL", 10, 160.0)

    report = build_performance_report(
        portfolio.initial_cash,
        portfolio.trades,
        portfolio.positions,
        {},
        {},
        portfolio.equity({}),
    )

    # The sell order gains 300 on the first lot and loses 200 on the second:
    # aggregate realized P&L is +100, so this is one winning exit, not one win
    # and one loss.
    assert report.realized_pnl == pytest.approx(100.0)
    assert report.winning_trades == 1
    assert report.losing_trades == 0
    assert report.win_rate_pct == pytest.approx(100.0)
    assert report.profit_factor == pytest.approx(float("inf"))
