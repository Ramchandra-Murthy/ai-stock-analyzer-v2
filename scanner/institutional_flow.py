"""NSE FII/FPI and DII cash-market flow helpers."""

from __future__ import annotations

import pandas as pd
import requests

NSE_FII_DII_URL = "https://www.nseindia.com/api/fiidiiTradeReact"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://www.nseindia.com/reports/fii-dii",
}


def _fetch_payload(timeout: int = 10) -> list[dict[str, object]]:
    session = requests.Session()
    session.headers.update(_HEADERS)
    session.get("https://www.nseindia.com", timeout=timeout)
    response = session.get(NSE_FII_DII_URL, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("NSE FII/DII response format was not a list.")
    return payload


def _normalize_payload(payload: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(payload)
    if frame.empty:
        return frame

    rename = {
        "category": "Category",
        "date": "Date",
        "buyValue": "Buy Value (₹ Cr)",
        "sellValue": "Sell Value (₹ Cr)",
        "netValue": "Net Value (₹ Cr)",
        "fiibuy": "FII Buy Value (₹ Cr)",
        "fiisell": "FII Sell Value (₹ Cr)",
        "fiinet": "FII Net Value (₹ Cr)",
        "diibuy": "DII Buy Value (₹ Cr)",
        "diisell": "DII Sell Value (₹ Cr)",
        "diinet": "DII Net Value (₹ Cr)",
    }
    frame = frame.rename(columns=rename)

    if {"FII Net Value (₹ Cr)", "DII Net Value (₹ Cr)"}.issubset(frame.columns):
        columns = [
            "Date",
            "FII Buy Value (₹ Cr)",
            "FII Sell Value (₹ Cr)",
            "FII Net Value (₹ Cr)",
            "DII Buy Value (₹ Cr)",
            "DII Sell Value (₹ Cr)",
            "DII Net Value (₹ Cr)",
        ]
        available = [column for column in columns if column in frame.columns]
        for column in available[1:]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame[available]

    required = [
        "Category",
        "Date",
        "Buy Value (₹ Cr)",
        "Sell Value (₹ Cr)",
        "Net Value (₹ Cr)",
    ]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"NSE FII/DII response is missing: {', '.join(missing)}")
    for column in required[2:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame[required]


def _category_rows(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for category, buy, sell, net in [
        ("FII/FPI", "FII Buy Value (₹ Cr)", "FII Sell Value (₹ Cr)", "FII Net Value (₹ Cr)"),
        ("DII", "DII Buy Value (₹ Cr)", "DII Sell Value (₹ Cr)", "DII Net Value (₹ Cr)"),
    ]:
        if net in frame.columns:
            row = {
                "Category": category,
                "Date": (
                    frame["Date"].iloc[0] if "Date" in frame.columns and not frame.empty else None
                ),
                "Buy Value (₹ Cr)": frame[buy].iloc[0] if buy in frame.columns else None,
                "Sell Value (₹ Cr)": frame[sell].iloc[0] if sell in frame.columns else None,
                "Net Value (₹ Cr)": frame[net].iloc[0],
            }
            rows.append(row)
    return pd.DataFrame(rows)


def fetch_fii_dii_flow(timeout: int = 10) -> pd.DataFrame:
    """Fetch the latest NSE FII/FPI and DII activity in category-row form."""
    payload = _fetch_payload(timeout)
    frame = _normalize_payload(payload)
    if {"FII Net Value (₹ Cr)", "DII Net Value (₹ Cr)"}.issubset(frame.columns):
        return _category_rows(frame)
    return frame


def fetch_fii_dii_history(timeout: int = 10) -> pd.DataFrame:
    """Fetch the historical FII/FPI and DII rows exposed by the NSE endpoint."""
    return _normalize_payload(_fetch_payload(timeout))
