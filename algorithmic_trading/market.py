"""Indian-market symbol helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketSymbol:
    """Exchange-aware symbol representation."""

    symbol: str
    exchange: str

    def __post_init__(self) -> None:
        exchange = self.exchange.upper()
        if exchange not in {"NSE", "BSE"}:
            raise ValueError("exchange must be NSE or BSE")
        object.__setattr__(self, "symbol", self.symbol.upper().strip())
        object.__setattr__(self, "exchange", exchange)

    @property
    def yfinance_symbol(self) -> str:
        if self.exchange == "NSE":
            return f"{self.symbol}.NS"
        return f"{self.symbol}.BO"


def make_market_symbol(symbol: str, exchange: str) -> MarketSymbol:
    cleaned = symbol.strip().upper()
    if cleaned.endswith(".NS") or cleaned.endswith(".BO"):
        cleaned = cleaned[:-3]
    return MarketSymbol(cleaned, exchange)
