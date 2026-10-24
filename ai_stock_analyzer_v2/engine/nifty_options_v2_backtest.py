"""Backtest engine for the frozen NIFTY Options Book V2 rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from engine.options_data import HistoricalOptionsData


@dataclass(frozen=True)
class V2BacktestTrade:
    """One monthly deep-ITM CALL trade from entry to expiry."""

    entry: object
    exit: object

    @property
    def points_pnl(self) -> float:
        return self.exit.ltp - self.entry.ltp

    @property
    def gross_pnl(self) -> float:
        return self.points_pnl


class NiftyOptionsV2Backtest:
    """Execute one no-management CALL trade using supplied historical data."""

    def __init__(self, data: HistoricalOptionsData) -> None:
        self.data = data

    def run_trade(
        self,
        *,
        expiry: date,
        strike: float,
        entry_date: date,
        exit_date: date,
    ) -> V2BacktestTrade:
        """Enter on entry_date and exit on exit_date without adjustment."""
        if exit_date < entry_date:
            raise ValueError("exit_date must not precede entry_date")
        entry = self.data.get_observation(expiry=expiry, strike=strike, observed_date=entry_date)
        exit_observation = self.data.get_observation(
            expiry=expiry, strike=strike, observed_date=exit_date
        )
        if not entry.is_itm:
            raise ValueError("V2 requires an ITM CALL strike at entry")
        return V2BacktestTrade(entry=entry, exit=exit_observation)
