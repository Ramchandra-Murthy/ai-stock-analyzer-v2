"""Trade journal analytics for AI paper trading."""

from __future__ import annotations

from dataclasses import dataclass

from .paper_trading import PaperTrade


@dataclass(frozen=True)
class TradeJournalRow:
    """Analytics for one completed paper-trade round trip."""

    symbol: str
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    return_pct: float
    holding_seconds: float
    entry_confidence_pct: float | None
    entry_reason: str
    exit_reason: str


def build_trade_journal(trades: list[PaperTrade]) -> list[TradeJournalRow]:
    """Match FIFO entries and exits into completed trade journal rows."""
    lots: dict[str, list[PaperTrade]] = {}
    journal: list[TradeJournalRow] = []

    for trade in trades:
        if trade.side == "BUY":
            lots.setdefault(trade.symbol, []).append(trade)
            continue

        remaining = trade.quantity
        while remaining > 0 and lots.get(trade.symbol):
            entry = lots[trade.symbol][0]
            matched = min(remaining, entry.quantity)
            pnl = matched * (trade.price - entry.price)
            journal.append(
                TradeJournalRow(
                    symbol=trade.symbol,
                    entry_price=entry.price,
                    exit_price=trade.price,
                    quantity=matched,
                    pnl=pnl,
                    return_pct=(trade.price / entry.price - 1.0) * 100.0,
                    holding_seconds=max(
                        0.0,
                        (trade.timestamp - entry.timestamp).total_seconds(),
                    ),
                    entry_confidence_pct=entry.confidence_pct,
                    entry_reason=entry.reason,
                    exit_reason=trade.reason,
                )
            )
            remaining -= matched
            if matched == entry.quantity:
                lots[trade.symbol].pop(0)
            else:
                lots[trade.symbol][0] = PaperTrade(
                    symbol=entry.symbol,
                    side=entry.side,
                    quantity=entry.quantity - matched,
                    price=entry.price,
                    value=(entry.quantity - matched) * entry.price,
                    cash_after=entry.cash_after,
                    signal=entry.signal,
                    confidence_pct=entry.confidence_pct,
                    reason=entry.reason,
                    timestamp=entry.timestamp,
                )

    return journal


def summarize_journal(
    rows: list[TradeJournalRow],
) -> list[dict[str, float | int | str]]:
    """Return symbol-level completed-trade statistics."""
    symbols = sorted({row.symbol for row in rows})
    summary: list[dict[str, float | int | str]] = []

    for symbol in symbols:
        symbol_rows = [row for row in rows if row.symbol == symbol]
        wins = [row.pnl for row in symbol_rows if row.pnl > 0]
        losses = [row.pnl for row in symbol_rows if row.pnl < 0]
        total_pnl = sum(row.pnl for row in symbol_rows)
        summary.append(
            {
                "symbol": symbol,
                "trades": len(symbol_rows),
                "wins": len(wins),
                "losses": len(losses),
                "win_rate_pct": (len(wins) / len(symbol_rows) * 100.0 if symbol_rows else 0.0),
                "total_pnl": total_pnl,
                "avg_pnl": total_pnl / len(symbol_rows) if symbol_rows else 0.0,
                "avg_return_pct": (
                    sum(row.return_pct for row in symbol_rows) / len(symbol_rows)
                    if symbol_rows
                    else 0.0
                ),
            }
        )

    return summary
