"""Tests for the realized paper-trade ledger."""

from algorithmic_trading.paper_trading import PaperFill
from algorithmic_trading.realized_trade_ledger import RealizedTradeLedger


def test_long_trade_is_realized_on_sell() -> None:
    ledger = RealizedTradeLedger()
    ledger.record_fill(
        PaperFill("RELIANCE", 10, 100.0, "BUY", 1000.0),
        signal="LONG",
        regime="trend",
        allocation_weight=0.10,
    )

    trades = ledger.record_fill(PaperFill("RELIANCE", 10, 112.0, "SELL", 1120.0))

    assert len(trades) == 1
    assert trades[0].side == "LONG"
    assert trades[0].quantity == 10
    assert trades[0].pnl == 120.0
    assert trades[0].signal == "LONG"
    assert trades[0].regime == "trend"
    assert trades[0].allocation_weight == 0.10
    assert ledger.open_quantity("RELIANCE") == 0


def test_short_trade_is_realized_on_buy_to_cover() -> None:
    ledger = RealizedTradeLedger()
    ledger.record_fill(PaperFill("TCS", 5, 200.0, "SELL", 1000.0))

    trades = ledger.record_fill(PaperFill("TCS", 5, 180.0, "BUY", 900.0))

    assert len(trades) == 1
    assert trades[0].side == "SHORT"
    assert trades[0].quantity == 5
    assert trades[0].pnl == 100.0


def test_partial_exit_uses_fifo() -> None:
    ledger = RealizedTradeLedger()
    ledger.record_fill(PaperFill("INFY", 10, 100.0, "BUY", 1000.0), signal="LONG")
    ledger.record_fill(PaperFill("INFY", 5, 110.0, "BUY", 550.0), signal="LONG")

    trades = ledger.record_fill(PaperFill("INFY", 12, 120.0, "SELL", 1440.0))

    assert [trade.quantity for trade in trades] == [10, 2]
    assert [trade.entry_price for trade in trades] == [100.0, 110.0]
    assert [trade.pnl for trade in trades] == [200.0, 20.0]
    assert ledger.open_quantity("INFY") == 3


def test_reversal_opens_remaining_quantity() -> None:
    ledger = RealizedTradeLedger()
    ledger.record_fill(PaperFill("SBIN", 10, 100.0, "BUY", 1000.0))

    trades = ledger.record_fill(PaperFill("SBIN", 15, 90.0, "SELL", 1350.0))

    assert len(trades) == 1
    assert trades[0].pnl == -100.0
    assert ledger.open_quantity("SBIN") == -5
    assert ledger.open_symbols() == ("SBIN",)
