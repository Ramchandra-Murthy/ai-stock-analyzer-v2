"""Paper portfolio engine for AI trading signals."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import isfinite

import pandas as pd

from .risk import RiskLimits


@dataclass(frozen=True)
class EquitySnapshot:
    """A timestamped paper-portfolio equity observation."""

    timestamp: datetime
    equity: float


@dataclass(frozen=True)
class PaperTrade:
    """A simulated paper-trading execution."""

    symbol: str
    side: str
    quantity: int
    price: float
    value: float
    cash_after: float
    signal: str | None = None
    confidence_pct: float | None = None
    reason: str = "manual"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class PaperPortfolio:
    """In-memory long-only paper portfolio."""

    initial_cash: float = 100_000.0
    cash: float = 100_000.0
    positions: dict[str, int] = field(default_factory=dict)
    trades: list[PaperTrade] = field(default_factory=list)
    equity_history: list[EquitySnapshot] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        if self.cash <= 0:
            self.cash = self.initial_cash

    def equity(self, prices: dict[str, float]) -> float:
        """Mark current positions to supplied latest prices."""
        market_value = 0.0
        for symbol, quantity in self.positions.items():
            if symbol not in prices:
                continue
            price = float(prices[symbol])
            if not isfinite(price) or price <= 0:
                raise ValueError(f"price for {symbol} must be finite and positive")
            market_value += quantity * price
        return float(self.cash + market_value)

    def record_equity(self, prices: dict[str, float]) -> EquitySnapshot:
        """Record a timestamped mark-to-market equity observation."""
        snapshot = EquitySnapshot(datetime.now(UTC), self.equity(prices))
        self.equity_history.append(snapshot)
        return snapshot

    def execute(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        *,
        signal: str | None = None,
        confidence_pct: float | None = None,
        reason: str = "manual",
    ) -> PaperTrade | None:
        """Execute a simulated market fill."""
        symbol = str(symbol).upper()
        side = str(side).upper()
        price = float(price)

        if quantity <= 0 or not isfinite(price) or price <= 0:
            raise ValueError("quantity must be positive and price must be finite and positive")
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")

        current = self.positions.get(symbol, 0)
        if side == "BUY":
            value = quantity * price
            if value > self.cash:
                return None
            self.cash -= value
            self.positions[symbol] = current + quantity
        else:
            quantity = min(quantity, current)
            if quantity <= 0:
                return None
            value = quantity * price
            self.cash += value
            remaining = current - quantity
            if remaining:
                self.positions[symbol] = remaining
            else:
                self.positions.pop(symbol, None)

        trade = PaperTrade(
            symbol,
            side,
            quantity,
            price,
            value,
            self.cash,
            signal,
            confidence_pct,
            reason,
        )
        self.trades.append(trade)
        return trade


def apply_ml_signals(
    portfolio: PaperPortfolio,
    signals: pd.DataFrame,
    prices: dict[str, float],
    *,
    capital_fraction: float = 0.20,
    max_positions: int = 5,
    risk_limits: RiskLimits | None = None,
) -> list[PaperTrade]:
    """Apply LONG/SHORT/FLAT ML signals to a long-only paper portfolio."""
    if not 0.0 < capital_fraction <= 1.0:
        raise ValueError("capital_fraction must be between 0 and 1")
    if max_positions < 1:
        raise ValueError("max_positions must be at least 1")

    required = {"symbol", "signal"}
    missing = required.difference(signals.columns)
    if missing:
        raise ValueError(f"signals missing columns: {sorted(missing)}")

    rows = signals.copy()
    rows["symbol"] = rows["symbol"].astype(str).str.upper()
    long_symbols = {row.symbol for row in rows.itertuples() if row.signal == "LONG"}

    trades: list[PaperTrade] = []
    for symbol in list(portfolio.positions):
        if symbol not in long_symbols and symbol in prices:
            fill = portfolio.execute(
                symbol,
                "SELL",
                portfolio.positions[symbol],
                prices[symbol],
                reason="ML signal exit",
            )
            if fill:
                trades.append(fill)

    available_slots = max_positions - len(portfolio.positions)
    if available_slots <= 0:
        return trades

    candidates = rows[(rows["signal"] == "LONG") & rows["symbol"].isin(prices)].copy()
    if "confidence_pct" in candidates.columns:
        candidates = candidates.sort_values("confidence_pct", ascending=False)

    target_symbols = [
        symbol for symbol in candidates["symbol"].tolist() if symbol not in portfolio.positions
    ][:available_slots]
    if not target_symbols:
        return trades

    if risk_limits is None:
        allocation = portfolio.cash * capital_fraction / len(target_symbols)
    else:
        current_market_value = sum(
            quantity * float(prices[symbol])
            for symbol, quantity in portfolio.positions.items()
            if symbol in prices
        )
        risk_allocation = risk_limits.allocation(
            portfolio.equity(prices),
            portfolio.cash,
            current_market_value,
            len(target_symbols),
        )
        allocation = min(
            portfolio.cash * capital_fraction / len(target_symbols),
            risk_allocation["per_candidate"],
        )

    for symbol in target_symbols:
        price = float(prices[symbol])
        quantity = int(allocation // price)
        signal_row = rows[rows["symbol"] == symbol].iloc[0]
        confidence = (
            float(signal_row["confidence_pct"]) if "confidence_pct" in signal_row.index else None
        )
        fill = portfolio.execute(
            symbol,
            "BUY",
            quantity,
            price,
            signal=str(signal_row["signal"]),
            confidence_pct=confidence,
            reason="ML signal entry",
        )
        if fill:
            trades.append(fill)

    return trades
