"""Top-10 market mover scanner with Chapter 4-10 workflow signals."""

from __future__ import annotations

import pandas as pd

from engine.live_integrated_scanner import scan_integrated_tickers
from scanner.market_scanner import _batch_change_screen
from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES

LIVE_TOP10_CANDIDATE_COUNT = 20
TOP10_ANALYSIS_PERIOD = "3mo"


def scan_top10_integrated(
    *,
    period: str = "6mo",
    interval: str = "1d",
) -> pd.DataFrame:
    """Return the ten largest liquid NSE/BSE daily movers with workflow signals."""
    # Keep the live page responsive by screening the first 20 curated NSE and
    # first 20 curated BSE candidates. The general scanner remains unchanged.
    del period, interval
    candidates = {
        "NSE": NSE_CANDIDATES[:LIVE_TOP10_CANDIDATE_COUNT],
        "BSE": BSE_CANDIDATES[:LIVE_TOP10_CANDIDATE_COUNT],
    }
    movers = _batch_change_screen(candidates)[:10]
    if not movers:
        return pd.DataFrame()

    normalized_movers = [
        (
            row[0],
            row[1],
            row[2],
            row[3] if len(row) > 3 else None,
        )
        for row in movers
    ]
    tickers = [ticker for ticker, _exchange, _change, _turnover in normalized_movers]
    changes = {ticker: change for ticker, _exchange, change, _turnover in normalized_movers}
    result = scan_integrated_tickers(
        tickers,
        period=TOP10_ANALYSIS_PERIOD,
        interval="1d",
    )
    if result.empty:
        return result

    result["Change %"] = result["Ticker"].map(changes)
    result["Change %"] = result["Change %"].round(2)
    return result.sort_values(
        "Change %", key=lambda values: values.abs(), ascending=False
    ).reset_index(drop=True)
