from __future__ import annotations

from core.identifiers import ISIN, CompanySymbol, ExchangeCode, Industry, Sector


def run_example() -> None:
    print("--- CORE-001C: Identifiers & Classifications Example ---")
    symbol = CompanySymbol("tcs")
    isin = ISIN("INE467B01029")
    exchange = ExchangeCode.NSE
    sector = Sector("Information Technology")
    industry = Industry("IT Services")

    print(f"Company: {symbol} on {exchange}")
    print(f"ISIN: {isin}")
    print(f"Classification: {sector} -> {industry}")
    print(f"Serialized Symbol: {symbol.to_dict()}")


if __name__ == "__main__":
    run_example()
