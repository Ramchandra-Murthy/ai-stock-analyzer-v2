"""Dhan-backed read-only intraday market-data provider for live scanners."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from services.dhan_market_data import DhanCredentials, DhanMarketData

_IST = timezone(timedelta(hours=5, minutes=30))


def _security_map() -> dict[str, int]:
    raw = os.getenv("DHAN_SECURITY_MAP_JSON", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    result: dict[str, int] = {}
    for symbol, security_id in parsed.items():
        try:
            result[str(symbol).strip().upper()] = int(security_id)
        except (TypeError, ValueError):
            continue
    return result


def _exchange_for_ticker(ticker: str) -> str:
    """Return the exchange implied by a Yahoo-style suffix (``.BO`` is BSE, else NSE)."""
    return "BSE" if str(ticker).strip().upper().endswith(".BO") else "NSE"


def resolve_security_id(ticker: str, mapping: dict[str, int]) -> int | None:
    """Look up a Dhan security ID without ever mixing up NSE and BSE instruments.

    Keys of the form ``"NSE:RELIANCE"`` or ``"BSE:500325"`` are preferred. A bare
    ``"RELIANCE"`` key predates exchange-qualified keys and is honoured for NSE only:
    using an NSE security ID with the BSE segment requests the wrong instrument.
    """
    exchange = _exchange_for_ticker(ticker)
    symbol = str(ticker).strip().upper().rsplit(".", 1)[0]
    qualified = mapping.get(f"{exchange}:{symbol}")
    if qualified is not None:
        return qualified
    return mapping.get(symbol) if exchange == "NSE" else None


def dhan_provider_enabled() -> bool:
    """Return True only when Dhan credentials and an instrument map are configured."""
    try:
        DhanCredentials.from_env()
    except Exception:
        return False
    return bool(_security_map())


def _response_frame(response: dict[str, Any]) -> pd.DataFrame:
    """Convert Dhan's column-oriented candle response to the scanner frame."""
    if not isinstance(response, dict):
        return pd.DataFrame()
    data = response.get("data", response)
    if not isinstance(data, dict):
        return pd.DataFrame()
    timestamps = data.get("timestamp", [])
    closes = data.get("close", [])
    opens = data.get("open", [])
    highs = data.get("high", [])
    lows = data.get("low", [])
    volumes = data.get("volume", [])
    if not timestamps or not closes:
        return pd.DataFrame()
    size = min(len(timestamps), len(closes))
    frame = pd.DataFrame(
        {
            "Open": list(opens)[:size],
            "High": list(highs)[:size],
            "Low": list(lows)[:size],
            "Close": list(closes)[:size],
            "Volume": list(volumes)[:size],
        }
    )
    frame.index = pd.to_datetime(list(timestamps)[:size], unit="s", utc=True).tz_convert(_IST)
    return frame.dropna(subset=["Close"]).sort_index()


def download_dhan_symbol_frames(
    tickers: list[str],
    *,
    interval: int = 1,
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Download recent Dhan candles for mapped NSE/BSE tickers."""
    mapping = _security_map()
    if not mapping or not dhan_provider_enabled():
        return {}, list(tickers)

    client = DhanMarketData()
    now = datetime.now(_IST)
    from_date = (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
    to_date = now.strftime("%Y-%m-%d %H:%M:%S")
    frames: dict[str, pd.DataFrame] = {}
    missing: list[str] = []

    for ticker in tickers:
        security_id = resolve_security_id(ticker, mapping)
        if security_id is None:
            missing.append(ticker)
            continue
        exchange_segment = "BSE_EQ" if _exchange_for_ticker(ticker) == "BSE" else "NSE_EQ"
        try:
            response = client.intraday_minute_data(
                security_id,
                exchange_segment,
                "EQUITY",
                from_date,
                to_date,
                interval=interval,
            )
            frame = _response_frame(response)
        except Exception:
            frame = pd.DataFrame()
        if frame.empty:
            missing.append(ticker)
        else:
            frames[ticker] = frame

    return frames, missing
