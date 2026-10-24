"""Tests for AI paper trade journal analytics."""

from datetime import UTC, datetime

import pytest

from ai_trading.paper_trading import PaperTrade
from ai_trading.trade_journal import build_trade_journal, summarize_journal


def test_trade_journal_matches_fifo_round_trip() -> None:
    entry_time = datetime(2026, 1, 1, tzinfo=UTC)
    exit_time = datetime(2026, 1, 1, 1, tzinfo=UTC)
    trades = [
        PaperTrade(
            "RELIANCE",
            "BUY",
            10,
            2_000.0,
            20_000.0,
            80_000.0,
            "LONG",
            82.5,
            "ML signal entry",
            entry_time,
        ),
        PaperTrade(
            "RELIANCE",
            "SELL",
            10,
            2_100.0,
            21_000.0,
            101_000.0,
            "LONG",
            82.5,
            "ML signal exit",
            exit_time,
        ),
    ]

    rows = build_trade_journal(trades)

    assert len(rows) == 1
    assert rows[0].pnl == pytest.approx(1_000.0)
    assert rows[0].return_pct == pytest.approx(5.0)
    assert rows[0].holding_seconds == pytest.approx(3_600.0)
    assert rows[0].entry_confidence_pct == pytest.approx(82.5)


def test_journal_summary_groups_symbols() -> None:
    trades = [
        PaperTrade("A", "BUY", 10, 100.0, 1_000.0, 9_000.0),
        PaperTrade("A", "SELL", 10, 110.0, 1_100.0, 10_100.0),
        PaperTrade("B", "BUY", 5, 200.0, 1_000.0, 9_100.0),
        PaperTrade("B", "SELL", 5, 190.0, 950.0, 10_050.0),
    ]

    summary = summarize_journal(build_trade_journal(trades))

    expected = [
        {
            "symbol": "A",
            "trades": 1,
            "wins": 1,
            "losses": 0,
            "win_rate_pct": pytest.approx(100.0),
            "total_pnl": pytest.approx(100.0),
            "avg_pnl": pytest.approx(100.0),
            "avg_return_pct": pytest.approx(10.0),
        },
        {
            "symbol": "B",
            "trades": 1,
            "wins": 0,
            "losses": 1,
            "win_rate_pct": pytest.approx(0.0),
            "total_pnl": pytest.approx(-50.0),
            "avg_pnl": pytest.approx(-50.0),
            "avg_return_pct": pytest.approx(-5.0),
        },
    ]

    assert summary == expected
