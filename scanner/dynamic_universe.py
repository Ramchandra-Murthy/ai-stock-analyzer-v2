from __future__ import annotations

import io
import json
import logging
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES

NSE_EQUITY_LIST_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
BSE_SECURITIES_URL = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
CACHE_TTL_SECONDS = 15 * 60
MIN_PRICE = 20.0
MIN_AVG_DAILY_TURNOVER = 2.0e7
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9&.-]+$")

_cached_nse_symbols: tuple[float, list[str]] | None = None
_cached_bse_symbols: tuple[float, list[str]] | None = None


def _download_nse_equity_list() -> list[str]:
    request = Request(
        NSE_EQUITY_LIST_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AI_STOCK_ANALYZER/1.0)",
            "Accept": "text/csv,*/*",
        },
    )
    with urlopen(request, timeout=15) as response:
        payload = response.read()

    frame = pd.read_csv(io.BytesIO(payload))
    if "SYMBOL" not in frame.columns:
        raise ValueError("NSE equity list does not contain SYMBOL")

    symbols = frame["SYMBOL"].astype(str).str.strip().str.upper()
    if "SERIES" in frame.columns:
        symbols = symbols[frame["SERIES"].astype(str).str.strip().eq("EQ")]

    return sorted(
        {
            symbol
            for symbol in symbols
            if symbol and symbol != "NAN" and SYMBOL_PATTERN.fullmatch(symbol)
        }
    )


def _download_bse_equity_list() -> list[str]:
    query = urlencode(
        {
            "scripcode": "",
            "Group": "",
            "industry": "",
            "segment": "Equity",
            "status": "Active",
        }
    )
    request = Request(
        f"{BSE_SECURITIES_URL}?{query}",
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AI_STOCK_ANALYZER/1.0)",
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://www.bseindia.com/",
            "Origin": "https://www.bseindia.com",
        },
    )
    with urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not isinstance(payload, list):
        raise ValueError(f"BSE securities response must be a list, got {type(payload).__name__}")

    valid_rows = [
        row
        for row in payload
        if isinstance(row, dict)
        and str(row.get("Status", "")).strip().lower() == "active"
        and str(row.get("Segment", "")).strip().lower() == "equity"
    ]
    symbols = {str(row.get("scrip_id", "")).strip().upper() for row in valid_rows}
    parsed = sorted(symbol for symbol in symbols if symbol and SYMBOL_PATTERN.fullmatch(symbol))
    logging.info(
        "BSE universe source=live raw_rows=%d active_equity_rows=%d parsed_symbols=%d",
        len(payload),
        len(valid_rows),
        len(parsed),
    )
    if not parsed:
        sample_keys = sorted(
            str(key) for row in payload[:3] if isinstance(row, dict) for key in row.keys()
        )
        raise ValueError(
            "BSE response contained no parseable active equity symbols; "
            f"sample field names={sample_keys}"
        )
    return parsed


def dynamic_nse_symbols() -> list[str]:
    """Return the current NSE equity universe, falling back to curated symbols."""
    global _cached_nse_symbols

    now = time.time()
    if _cached_nse_symbols and now - _cached_nse_symbols[0] < CACHE_TTL_SECONDS:
        return _cached_nse_symbols[1]

    try:
        symbols = _download_nse_equity_list()
        if symbols:
            _cached_nse_symbols = (now, symbols)
            return symbols
    except Exception:
        pass

    return list(NSE_CANDIDATES)


def dynamic_bse_symbols() -> list[str]:
    """Return active BSE equities, logging live-source coverage and fallback reason."""
    global _cached_bse_symbols

    now = time.time()
    if _cached_bse_symbols and now - _cached_bse_symbols[0] < CACHE_TTL_SECONDS:
        logging.debug(
            "BSE universe source=cache symbols=%d",
            len(_cached_bse_symbols[1]),
        )
        return _cached_bse_symbols[1]

    try:
        symbols = _download_bse_equity_list()
        if symbols:
            _cached_bse_symbols = (now, symbols)
            logging.info(
                "BSE universe source=live symbols=%d curated_fallback_symbols=%d",
                len(symbols),
                len(BSE_CANDIDATES),
            )
            return symbols
        fallback_reason = "live source returned an empty symbol list"
    except Exception as exc:
        fallback_reason = f"{type(exc).__name__}: {exc}"

    fallback = list(BSE_CANDIDATES)
    logging.warning(
        "BSE universe fallback=curated reason=%s fallback_symbols=%d",
        fallback_reason,
        len(fallback),
    )
    return fallback


def merge_nse_universe(extra_symbols: list[str] | None = None) -> list[str]:
    """Merge the live NSE list with curated symbols so known names are never lost."""
    symbols = set(dynamic_nse_symbols())
    symbols.update(NSE_CANDIDATES)
    if extra_symbols:
        symbols.update(symbol.strip().upper() for symbol in extra_symbols if symbol.strip())
    return sorted(symbols)


def merge_bse_universe(extra_symbols: list[str] | None = None) -> list[str]:
    """Merge the live BSE list with curated symbols so known names are never lost."""
    symbols = set(dynamic_bse_symbols())
    symbols.update(BSE_CANDIDATES)
    if extra_symbols:
        symbols.update(symbol.strip().upper() for symbol in extra_symbols if symbol.strip())
    return sorted(symbols)


def passes_liquidity_filter(latest_price: float, average_volume: float) -> bool:
    """Keep reasonably liquid stocks suitable for an intraday opportunity scan."""
    return latest_price >= MIN_PRICE and latest_price * average_volume >= MIN_AVG_DAILY_TURNOVER
