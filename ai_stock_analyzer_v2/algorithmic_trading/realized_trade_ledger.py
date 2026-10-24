"""Realized-trade ledger for paper-trading feedback and attribution.

The ledger consumes simulated fills and converts completed position changes into
auditable realized trades. Matching is FIFO and supports both long and short
positions without connecting to a broker.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from algorithmic_trading.paper_trading import PaperFill


@dataclass(frozen=True)
class RealizedTrade:
    """A completed trade matched from an entry and an exit fill."""

    symbol: str
    quantity: int
    side: str
    entry_price: float
    exit_price: float
    pnl: float
    signal: str | None = None
    regime: str | None = None
    allocation_weight: float | None = None


@dataclass
class _OpenLot:
    """Internal FIFO position lot."""

    symbol: str
    quantity: int
    entry_price: float
    signal: str | None
    regime: str | None
    allocation_weight: float | None


@dataclass
class RealizedTradeLedger:
    """FIFO ledger that records only completed paper trades."""

    _lots: dict[str, list[_OpenLot]] = field(default_factory=dict)
    trades: list[RealizedTrade] = field(default_factory=list)

    def record_fill(
        self,
        fill: PaperFill,
        *,
        signal: str | None = None,
        regime: str | None = None,
        allocation_weight: float | None = None,
    ) -> list[RealizedTrade]:
        """Apply a fill and return any trades completed by that fill.

        BUY fills open or reduce short lots. SELL fills open or reduce long
        lots. A reversal is split automatically so the remaining quantity
        becomes a new lot.
        """
        if fill.quantity <= 0:
            raise ValueError("fill quantity must be greater than zero")
        if fill.price <= 0:
            raise ValueError("fill price must be greater than zero")
        side = fill.side.upper()
        if side not in {"BUY", "SELL"}:
            raise ValueError("fill side must be BUY or SELL")

        signed_quantity = fill.quantity if side == "BUY" else -fill.quantity
        lots = self._lots.setdefault(fill.symbol, [])
        realized: list[RealizedTrade] = []

        while signed_quantity and lots and self._same_position_side(lots[0], signed_quantity):
            lot = lots[0]
            matched = min(abs(signed_quantity), abs(lot.quantity))
            exit_price = fill.price
            pnl_per_share = (
                exit_price - lot.entry_price if lot.quantity > 0 else lot.entry_price - exit_price
            )
            trade_side = "LONG" if lot.quantity > 0 else "SHORT"
            trade = RealizedTrade(
                symbol=fill.symbol,
                quantity=matched,
                side=trade_side,
                entry_price=lot.entry_price,
                exit_price=exit_price,
                pnl=pnl_per_share * matched,
                signal=lot.signal,
                regime=lot.regime,
                allocation_weight=lot.allocation_weight,
            )
            realized.append(trade)
            self.trades.append(trade)

            signed_quantity += matched if signed_quantity < 0 else -matched
            lot.quantity += -matched if lot.quantity > 0 else matched
            if lot.quantity == 0:
                lots.pop(0)

        if signed_quantity:
            lots.append(
                _OpenLot(
                    symbol=fill.symbol,
                    quantity=signed_quantity,
                    entry_price=fill.price,
                    signal=signal,
                    regime=regime,
                    allocation_weight=allocation_weight,
                )
            )

        if not lots:
            self._lots.pop(fill.symbol, None)

        return realized

    def open_quantity(self, symbol: str) -> int:
        """Return the current signed open quantity for one symbol."""
        return sum(lot.quantity for lot in self._lots.get(symbol, []))

    def open_symbols(self) -> tuple[str, ...]:
        """Return symbols with an open paper-trading lot."""
        return tuple(sorted(self._lots))

    def reset(self) -> None:
        """Clear open lots and realized trade history."""
        self._lots.clear()
        self.trades.clear()

    @staticmethod
    def _same_position_side(lot: _OpenLot, signed_quantity: int) -> bool:
        return (lot.quantity > 0 and signed_quantity < 0) or (
            lot.quantity < 0 and signed_quantity > 0
        )
