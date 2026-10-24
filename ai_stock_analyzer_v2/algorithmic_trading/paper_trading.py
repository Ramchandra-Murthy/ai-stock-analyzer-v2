"""Paper-trading ledger for the NSE/BSE algorithmic research engine.

This module simulates order fills and portfolio accounting. It never connects
to a broker and never submits live orders.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PaperFill:
    """A simulated fill produced by a paper-trading order."""

    symbol: str
    quantity: int
    price: float
    side: str
    cost: float


@dataclass
class PaperPortfolio:
    """Cash and positions maintained by the paper-trading simulator."""

    cash: float
    positions: dict[str, int] = field(default_factory=dict)
    fills: list[PaperFill] = field(default_factory=list)

    def submit_market_order(
        self,
        symbol: str,
        quantity: int,
        price: float,
    ) -> PaperFill:
        """Simulate a market order filled at the supplied reference price."""
        if not symbol.strip():
            raise ValueError("symbol must not be empty")
        if quantity == 0:
            raise ValueError("quantity must not be zero")
        if price <= 0:
            raise ValueError("price must be greater than zero")

        side = "BUY" if quantity > 0 else "SELL"
        absolute_quantity = abs(quantity)
        notional = absolute_quantity * price

        if side == "BUY":
            if notional > self.cash:
                raise ValueError("insufficient paper cash")
            self.cash -= notional
        else:
            self.cash += notional

        self.positions[symbol] = self.positions.get(symbol, 0) + quantity
        if self.positions[symbol] == 0:
            del self.positions[symbol]

        fill = PaperFill(
            symbol=symbol,
            quantity=absolute_quantity,
            price=price,
            side=side,
            cost=notional,
        )
        self.fills.append(fill)
        return fill

    def mark_to_market(self, prices: dict[str, float]) -> float:
        """Return current paper equity using supplied market prices."""
        equity = self.cash
        for symbol, quantity in self.positions.items():
            price = prices.get(symbol)
            if price is None or price <= 0:
                raise ValueError(f"valid price required for {symbol}")
            equity += quantity * price
        return equity
