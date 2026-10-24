"""Download daily OHLC data for the Fibonacci-Gann Research Lab CSV format.

Examples:
    python scripts/make_research_csv.py
    python scripts/make_research_csv.py --symbol ^NSEI --start 2021-01-01
    python scripts/make_research_csv.py --symbol RELIANCE.NS --start 2021-01-01

This utility downloads prices only. It does not generate Fibonacci-Gann signals.
The signal column is initialized to False and must be populated using a documented,
causal strategy before the CSV is used to evaluate a strategy.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yfinance as yf


def download_research_csv(
    symbol: str,
    start: str,
    end: str | None = None,
    output: str | Path | None = None,
) -> Path:
    """Download daily OHLC prices and save the Research Lab CSV schema."""
    data = yf.download(
        symbol,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=False,
        progress=False,
        group_by="column",
    )
    if data.empty:
        raise ValueError(
            f"No historical data returned for {symbol!r}. "
            "Check the symbol/date range or try again later."
        )

    # Some yfinance versions return a MultiIndex even for one ticker.
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    missing = {"Open", "High", "Low", "Close"} - set(data.columns)
    if missing:
        raise ValueError(f"Downloaded data is missing OHLC columns: {sorted(missing)}")

    data = data.reset_index()
    date_col = "Date" if "Date" in data.columns else "Datetime"
    result = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(data[date_col]).dt.strftime("%Y-%m-%d"),
            "open": pd.to_numeric(data["Open"], errors="coerce"),
            "high": pd.to_numeric(data["High"], errors="coerce"),
            "low": pd.to_numeric(data["Low"], errors="coerce"),
            "close": pd.to_numeric(data["Close"], errors="coerce"),
        }
    )
    result = result.dropna(subset=["timestamp", "open", "high", "low", "close"])
    result = result.sort_values("timestamp").drop_duplicates("timestamp")

    prices = result[["open", "high", "low", "close"]]
    valid = (
        (prices > 0).all(axis=1)
        & (result["high"] >= prices[["open", "low", "close"]].max(axis=1))
        & (result["low"] <= prices[["open", "high", "close"]].min(axis=1))
    )
    result = result.loc[valid].reset_index(drop=True)
    if result.empty:
        raise ValueError("No valid OHLC rows remained after validation.")

    # Placeholder only: no strategy signals are inferred from price data.
    result["signal"] = False
    output_path = Path(output or f"{symbol.replace('^', '').replace('.', '_')}_research.csv")
    result.to_csv(output_path, index=False)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="RELIANCE.NS", help="Yahoo Finance symbol")
    parser.add_argument("--start", default="2021-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="End date YYYY-MM-DD (exclusive)")
    parser.add_argument("--output", default=None, help="Output CSV path")
    args = parser.parse_args()

    try:
        output = download_research_csv(args.symbol, args.start, args.end, args.output)
    except (ValueError, KeyError, OSError) as exc:
        raise SystemExit(f"Could not create research CSV: {exc}") from exc

    result = pd.read_csv(output)
    print(f"Saved {len(result)} daily rows to {output.resolve()}")
    print(
        "IMPORTANT: signal is False for every row; add actual strategy signals before backtesting."
    )
    print(result.head().to_string(index=False))


if __name__ == "__main__":
    main()
