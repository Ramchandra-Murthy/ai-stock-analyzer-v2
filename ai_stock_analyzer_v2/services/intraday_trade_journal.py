"""Session-local trade journal helpers for intraday review."""

# fmt: off

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

JOURNAL_COLUMNS = [
    "Timestamp",
    "Symbol",
    "Exchange",
    "Side",
    "Setup",
    "Entry",
    "Stop Loss",
    "Target",
    "Exit",
    "Quantity",
    "Risk",
    "Planned R:R",
    "PnL",
    "Outcome",
    "Reason",
    "Lesson",
]


def add_trade(
    history: list[dict[str, Any]] | None,
    *,
    timestamp: datetime,
    symbol: str,
    exchange: str,
    side: str,
    setup: str,
    entry: float,
    stop_loss: float,
    target: float,
    exit_price: float | None,
    quantity: int,
    reason: str,
    lesson: str,
) -> list[dict[str, Any]]:
    """Add one completed or open trade record to the session journal."""
    risk = abs(entry - stop_loss) * quantity
    planned_rr = _planned_rr(entry, stop_loss, target, side)
    pnl = _pnl(entry, exit_price, quantity, side)
    outcome = _outcome(pnl, exit_price)

    record = {
        "Timestamp": timestamp.isoformat(),
        "Symbol": symbol.strip().upper(),
        "Exchange": exchange.strip().upper(),
        "Side": side.upper(),
        "Setup": setup.strip(),
        "Entry": float(entry),
        "Stop Loss": float(stop_loss),
        "Target": float(target),
        "Exit": float(exit_price) if exit_price is not None else None,
        "Quantity": int(quantity),
        "Risk": round(risk, 2),
        "Planned R:R": round(planned_rr, 2) if planned_rr is not None else None,
        "PnL": round(pnl, 2) if pnl is not None else None,
        "Outcome": outcome,
        "Reason": reason.strip(),
        "Lesson": lesson.strip(),
    }
    return list(history or []) + [record]


def journal_frame(history: list[dict[str, Any]] | None) -> pd.DataFrame:
    """Return journal records in a stable display order."""
    frame = pd.DataFrame(history or [])
    if frame.empty:
        return pd.DataFrame(columns=JOURNAL_COLUMNS)
    return frame.reindex(columns=JOURNAL_COLUMNS)


def journal_summary(history: list[dict[str, Any]] | None) -> pd.DataFrame:
    """Return descriptive session statistics for recorded trades."""
    frame = journal_frame(history)
    if frame.empty:
        return pd.DataFrame(
            [{"Trades": 0, "Closed": 0, "Winners": 0, "Losers": 0, "Net PnL": 0.0}]
        )

    pnl = pd.to_numeric(frame["PnL"], errors="coerce")
    closed = pnl.notna()
    winners = (pnl > 0).sum()
    losers = (pnl < 0).sum()
    return pd.DataFrame(
        [
            {
                "Trades": len(frame),
                "Closed": int(closed.sum()),
                "Winners": int(winners),
                "Losers": int(losers),
                "Net PnL": round(float(pnl.sum()), 2),
            }
        ]
    )


def _planned_rr(entry: float, stop_loss: float, target: float, side: str) -> float | None:
    risk = abs(entry - stop_loss)
    if risk <= 0:
        return None
    reward = target - entry if side.upper() == "LONG" else entry - target
    if reward <= 0:
        return None
    return reward / risk


def _pnl(
    entry: float,
    exit_price: float | None,
    quantity: int,
    side: str,
) -> float | None:
    if exit_price is None:
        return None
    move = exit_price - entry if side.upper() == "LONG" else entry - exit_price
    return move * quantity


def _outcome(pnl: float | None, exit_price: float | None) -> str:
    if exit_price is None:
        return "OPEN"
    if pnl is None:
        return "OPEN"
    if pnl > 0:
        return "WIN"
    if pnl < 0:
        return "LOSS"
    return "FLAT"

# fmt: on
