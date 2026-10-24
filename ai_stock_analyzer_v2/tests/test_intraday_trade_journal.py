"""Tests for the intraday trade journal."""

from datetime import datetime

from services.intraday_trade_journal import add_trade, journal_frame, journal_summary


def test_add_trade_calculates_long_risk_rr_and_pnl():
    history = add_trade(
        [],
        timestamp=datetime.fromisoformat("2026-09-21T12:00:00+05:30"),
        symbol="TEST",
        exchange="NSE",
        side="LONG",
        setup="ORB",
        entry=100,
        stop_loss=98,
        target=104,
        exit_price=103,
        quantity=10,
        reason="Breakout with volume",
        lesson="Wait for confirmation",
    )

    record = history[0]
    assert record["Risk"] == 20.0
    assert record["Planned R:R"] == 2.0
    assert record["PnL"] == 30.0
    assert record["Outcome"] == "WIN"


def test_short_trade_pnl_and_open_status():
    history = add_trade(
        [],
        timestamp=datetime.fromisoformat("2026-09-21T12:05:00+05:30"),
        symbol="TEST",
        exchange="BSE",
        side="SHORT",
        setup="VWAP",
        entry=100,
        stop_loss=102,
        target=96,
        exit_price=None,
        quantity=5,
        reason="Rejection at VWAP",
        lesson="",
    )

    assert history[0]["Risk"] == 10.0
    assert history[0]["Planned R:R"] == 2.0
    assert history[0]["PnL"] is None
    assert history[0]["Outcome"] == "OPEN"


def test_journal_summary_is_descriptive():
    history = add_trade(
        [],
        timestamp=datetime.fromisoformat("2026-09-21T12:00:00+05:30"),
        symbol="TEST",
        exchange="NSE",
        side="LONG",
        setup="Momentum",
        entry=100,
        stop_loss=99,
        target=102,
        exit_price=101,
        quantity=10,
        reason="Momentum",
        lesson="Keep stop fixed",
    )
    history = add_trade(
        history,
        timestamp=datetime.fromisoformat("2026-09-21T12:05:00+05:30"),
        symbol="TEST2",
        exchange="NSE",
        side="LONG",
        setup="Breakout",
        entry=100,
        stop_loss=99,
        target=102,
        exit_price=98,
        quantity=10,
        reason="Breakout failed",
        lesson="Avoid weak volume",
    )

    summary = journal_summary(history).iloc[0]
    assert summary["Trades"] == 2
    assert summary["Closed"] == 2
    assert summary["Winners"] == 1
    assert summary["Losers"] == 1
    assert summary["Net PnL"] == -10.0
    assert list(journal_frame(history).columns)[0] == "Timestamp"
