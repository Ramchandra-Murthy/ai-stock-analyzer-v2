"""Book V1.0 strategy for long NIFTY ITM CALL trades."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Trade:
    """One monthly NIFTY CALL trade."""

    entry_date: date
    exit_date: date
    spot_entry: float
    spot_exit: float
    expiry: date
    strike: float
    entry_ltp: float
    exit_ltp: float
    lot_size: int

    @property
    def points_pnl(self) -> float:
        """Return option P&L in index points."""
        return self.exit_ltp - self.entry_ltp

    @property
    def gross_pnl(self) -> float:
        """Return gross P&L for the configured lot size."""
        return self.points_pnl * self.lot_size


class BookV1Strategy:
    """Implement the book monthly long-ITM-CALL holding model."""

    def create_trade(
        self,
        *,
        entry_date: date,
        exit_date: date,
        spot_entry: float,
        spot_exit: float,
        strike: float,
        entry_ltp: float,
        exit_ltp: float,
        lot_size: int,
    ) -> Trade:
        """Create a trade without applying intervention rules."""
        if lot_size <= 0:
            raise ValueError("lot_size must be positive")
        if entry_ltp < 0 or exit_ltp < 0:
            raise ValueError("option LTP values must be non-negative")

        return Trade(
            entry_date=entry_date,
            exit_date=exit_date,
            spot_entry=spot_entry,
            spot_exit=spot_exit,
            expiry=exit_date,
            strike=strike,
            entry_ltp=entry_ltp,
            exit_ltp=exit_ltp,
            lot_size=lot_size,
        )
