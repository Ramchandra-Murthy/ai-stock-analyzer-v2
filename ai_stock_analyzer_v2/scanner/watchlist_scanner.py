"""Scan symbols saved in the user's personal watchlist."""

from typing import Any

import pandas as pd

from services.analyzer import analyze_stock


def _normalize_ticker(symbol: str) -> str:
    value = str(symbol).strip().upper()
    if value.endswith((".NS", ".BO")):
        return value
    # The existing watchlist stores exchange-qualified symbols. For older or
    # manually entered unqualified entries, default to NSE convention.
    return f"{value}.NS" if value else ""


def scan_watchlist(symbols: list[str]) -> pd.DataFrame:
    """Analyze each saved symbol directly; do not substitute broad-universe movers."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for symbol in symbols:
        ticker = _normalize_ticker(symbol)
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        try:
            result = analyze_stock(ticker)
            last = result["last"]
            signal = result["signal"]
            trend = result["trend"]
            rows.append(
                {
                    "Symbol": ticker.removesuffix(".NS").removesuffix(".BO"),
                    "Exchange": "BSE" if ticker.endswith(".BO") else "NSE",
                    "Price": round(float(last["Close"]), 2),
                    "Trend": trend["Trend"],
                    "RSI": round(float(last["RSI_14"]), 2),
                    "MACD": round(float(last["MACD"]), 2),
                    "ATR": round(float(last["ATR"]), 2),
                    "AI Score": signal["Score"],
                    "Confidence": signal["Confidence"],
                    "Risk": "Medium",
                    "Recommendation": signal["Recommendation"],
                }
            )
        except Exception:
            # One unavailable/invalid ticker must not prevent the rest of the list.
            continue
    if not rows:
        return pd.DataFrame()
    return (
        pd.DataFrame(rows)
        .sort_values(by=["AI Score", "Confidence"], ascending=[False, False])
        .reset_index(drop=True)
    )
