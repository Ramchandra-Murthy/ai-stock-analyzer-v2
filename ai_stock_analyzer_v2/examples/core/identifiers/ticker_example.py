from __future__ import annotations

from core.identifiers.ticker import Ticker
from core.types.enums import MarketExchange


def run_example() -> None:
    print("--- CORE-001C: Identifiers & Enums Example ---")
    ticker = Ticker("tcs", MarketExchange.NSE)
    print(f"Instrument Ticker: {ticker.symbol} on Exchange: {ticker.exchange}")
    print(f"Serialized Ticker: {ticker.to_dict()}")


if __name__ == "__main__":
    run_example()
