"""Simulation-only paper trading for the NIFTY Options Book V2 strategy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite

from strategy.nifty_options_v2 import NiftyCallContract


@dataclass(frozen=True)
class PaperTrade:
    """One simulated NIFTY CALL paper trade."""

    contract: NiftyCallContract
    entry_date: date
    entry_ltp: float
    exit_date: date | None = None
    exit_ltp: float | None = None

    @property
    def points_pnl(self) -> float | None:
        """Return points P&L once the simulated trade is closed."""
        if self.exit_ltp is None:
            return None
        return self.exit_ltp - self.entry_ltp


class NiftyOptionsV2PaperTrader:
    """Run one monthly Book V2 trade at a time without broker execution."""

    def __init__(self) -> None:
        self.active_trade: PaperTrade | None = None
        self.completed_trades: list[PaperTrade] = []

    def enter(
        self,
        *,
        contract: NiftyCallContract,
        observed_date: date,
        spot: float,
        ltp: float,
    ) -> PaperTrade:
        """Record a simulated ITM CALL entry using a supplied market observation."""
        if self.active_trade is not None:
            raise ValueError("a paper trade is already active")
        if observed_date >= contract.expiry:
            raise ValueError("entry must occur before contract expiry")
        if not isfinite(spot) or spot <= 0:
            raise ValueError("spot must be finite and positive")
        if spot <= contract.strike:
            raise ValueError("paper entry requires an ITM CALL")
        if not isfinite(ltp) or ltp < 0:
            raise ValueError("ltp must be finite and non-negative")

        trade = PaperTrade(
            contract=contract,
            entry_date=observed_date,
            entry_ltp=ltp,
        )
        self.active_trade = trade
        return trade

    def mark_exit(
        self,
        *,
        observed_date: date,
        ltp: float,
    ) -> PaperTrade:
        """Record a supplied exit observation and close the active paper trade."""
        if self.active_trade is None:
            raise ValueError("no active paper trade")
        if observed_date < self.active_trade.entry_date:
            raise ValueError("exit cannot precede entry")
        if observed_date > self.active_trade.contract.expiry:
            raise ValueError("exit cannot follow contract expiry")
        if not isfinite(ltp) or ltp < 0:
            raise ValueError("ltp must be finite and non-negative")

        closed = PaperTrade(
            contract=self.active_trade.contract,
            entry_date=self.active_trade.entry_date,
            entry_ltp=self.active_trade.entry_ltp,
            exit_date=observed_date,
            exit_ltp=ltp,
        )
        self.completed_trades.append(closed)
        self.active_trade = None
        return closed
