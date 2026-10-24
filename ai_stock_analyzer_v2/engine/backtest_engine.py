# ruff: noqa: I001

"""Backtest execution engine for prepared NIFTY option observations."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from strategy.book_v1 import BookV1Strategy

REQUIRED_COLUMNS = (
    "entry_date",
    "exit_date",
    "spot_entry",
    "spot_exit",
    "strike",
    "entry_ltp",
    "exit_ltp",
    "lot_size",
)


class BacktestEngine:
    """Run Book V1 trades without modifying positions after entry."""

    def __init__(self, strategy: BookV1Strategy) -> None:
        self.strategy = strategy

    def run(self, trades: pd.DataFrame) -> pd.DataFrame:
        """Execute prepared trades and return one result row per trade."""
        missing = [column for column in REQUIRED_COLUMNS if column not in trades.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        results: list[dict[str, Any]] = []
        for row in trades.itertuples(index=False):
            trade = self.strategy.create_trade(
                entry_date=_as_date(row.entry_date),
                exit_date=_as_date(row.exit_date),
                spot_entry=float(row.spot_entry),
                spot_exit=float(row.spot_exit),
                strike=float(row.strike),
                entry_ltp=float(row.entry_ltp),
                exit_ltp=float(row.exit_ltp),
                lot_size=int(row.lot_size),
            )
            results.append(
                {
                    "entry_date": trade.entry_date,
                    "exit_date": trade.exit_date,
                    "spot_entry": trade.spot_entry,
                    "spot_exit": trade.spot_exit,
                    "strike": trade.strike,
                    "entry_ltp": trade.entry_ltp,
                    "exit_ltp": trade.exit_ltp,
                    "lot_size": trade.lot_size,
                    "points_pnl": trade.points_pnl,
                    "gross_pnl": trade.gross_pnl,
                }
            )

        return pd.DataFrame(results)


def _as_date(value: object) -> date:
    """Convert a pandas or Python date-like value to date."""
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()
