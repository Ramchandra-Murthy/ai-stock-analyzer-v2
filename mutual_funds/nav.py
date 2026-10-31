"""Fetch and parse mutual-fund NAV history from the free mfapi.in service (AMFI data).

Network access is isolated in ``default_fetch`` and every public function accepts an
injected ``fetch`` callable, so parsing and analytics are testable offline. NAVs are the
published end-of-day values; mfapi can lag AMFI by a day and is a third-party service.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

import pandas as pd

BASE_URL = "https://api.mfapi.in"
Fetch = Callable[[str], Any]


def default_fetch(url: str, attempts: int = 3, pause: float = 1.0) -> Any:
    """GET JSON from mfapi.in, retrying transient network errors with a short back-off."""
    if not url.startswith(BASE_URL + "/"):
        raise ValueError("Only mfapi.in URLs are allowed.")
    request = urllib.request.Request(url, headers={"User-Agent": "ai-stock-analyzer/2"})
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except (OSError, json.JSONDecodeError) as exc:  # URLError/HTTPError are OSErrors
            last = exc
            if isinstance(exc, urllib.error.HTTPError) and 400 <= exc.code < 500:
                break  # a client error will not fix itself
            if attempt < attempts - 1:
                time.sleep(pause * (attempt + 1))
    raise ConnectionError(f"Could not reach mfapi.in ({last}). Check your network and retry.")


def parse_nav_response(payload: Any) -> tuple[dict[str, Any], pd.Series]:
    """(metadata, NAV series sorted by date, positive values only)."""
    if not isinstance(payload, dict) or "data" not in payload:
        raise ValueError("Unexpected NAV response: missing 'data'.")
    meta = dict(payload.get("meta") or {})
    rows = payload["data"]
    if not rows:
        raise ValueError("The scheme has no NAV history.")
    frame = pd.DataFrame(rows)
    if not {"date", "nav"} <= set(frame.columns):
        raise ValueError("Unexpected NAV response: rows need 'date' and 'nav'.")
    dates = pd.to_datetime(frame["date"], format="%d-%m-%Y", errors="coerce")
    nav = pd.to_numeric(frame["nav"], errors="coerce")
    series = pd.Series(nav.to_numpy(), index=dates).dropna()
    series = series[(series > 0) & series.index.notna()]
    series = series[~series.index.duplicated(keep="last")].sort_index()
    if len(series) < 2:
        raise ValueError("Not enough valid NAV observations.")
    series.name = str(meta.get("scheme_name", "NAV"))
    return meta, series


def fetch_scheme(code: int | str, fetch: Fetch = default_fetch) -> tuple[dict[str, Any], pd.Series]:
    code_text = str(code).strip()
    if not code_text.isdigit():
        raise ValueError("Scheme code must be numeric.")
    return parse_nav_response(fetch(f"{BASE_URL}/mf/{code_text}"))


def search_schemes(query: str, fetch: Fetch = default_fetch, limit: int = 25) -> pd.DataFrame:
    text = query.strip()
    if len(text) < 3:
        raise ValueError("Type at least 3 characters to search.")
    result = fetch(f"{BASE_URL}/mf/search?q={urllib.parse.quote(text)}")
    if not isinstance(result, list):
        raise ValueError("Unexpected search response.")
    frame = pd.DataFrame(result)
    if frame.empty or not {"schemeCode", "schemeName"} <= set(frame.columns):
        return pd.DataFrame(columns=["schemeCode", "schemeName"])
    return frame[["schemeCode", "schemeName"]].head(limit).reset_index(drop=True)


def is_direct_growth(name: str) -> bool:
    lower = name.lower()
    return (
        "direct" in lower and "growth" in lower and "idcw" not in lower and "dividend" not in lower
    )
