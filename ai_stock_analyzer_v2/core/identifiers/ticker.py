from __future__ import annotations

from dataclasses import dataclass

from core.primitives.value_object import ValueObject
from core.types.enums import MarketExchange


@dataclass(frozen=True, order=True)
class Ticker(ValueObject):
    """Standardized instrument ticker symbol combined with an exchange."""

    symbol: str
    exchange: MarketExchange

    def __init__(self, symbol: str, exchange: MarketExchange | str) -> None:
        if not symbol or not symbol.strip():
            raise ValueError("Ticker symbol cannot be empty")
        object.__setattr__(self, "symbol", symbol.strip().upper())
        object.__setattr__(self, "exchange", MarketExchange(exchange))

    def to_dict(self) -> dict[str, str]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange.value,
        }
