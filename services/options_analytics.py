"""Options analytics providers for the Streamlit scanner.

Dhan is the primary provider for Indian index option chains. NSE and Yahoo Finance
remain fallbacks for environments where Dhan is not configured or unavailable.
Provider availability and timestamps are surfaced rather than inferred.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, replace

import pandas as pd
import yfinance as yf
from curl_cffi import requests as curl_requests

from services.dhan_market_data import DhanCredentials, DhanMarketData

OPTIONS_UNDERLYINGS = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
}

DHAN_OPTION_UNDERLYINGS = {
    "NIFTY": (13, "IDX_I"),
    "BANKNIFTY": (25, "IDX_I"),
    "FINNIFTY": (27, "IDX_I"),
}

NSE_HOME_URL = "https://www.nseindia.com/"
NSE_OPTION_CHAIN_PAGE_URL = "https://www.nseindia.com/option-chain"
NSE_ALL_INDICES_URL = "https://www.nseindia.com/api/allIndices"
NSE_OPTION_CHAIN_URL = "https://www.nseindia.com/api/option-chain-v3"
NSE_OPTION_CHAIN_CONTRACT_INFO_URL = "https://www.nseindia.com/api/option-chain-contract-info"
NSE_HEADERS = {
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.nseindia.com",
    "Referer": "https://www.nseindia.com/option-chain",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0 Safari/537.36"
    ),
}

CHAIN_COLUMNS = [
    "strike",
    "CE LTP",
    "CE volume",
    "CE OI",
    "CE OI change",
    "CE IV",
    "PE LTP",
    "PE volume",
    "PE OI",
    "PE OI change",
    "PE IV",
    "PCR OI",
]


@dataclass(frozen=True)
class OptionChainResult:
    """Provider result with explicit availability diagnostics."""

    underlying: str
    provider_symbol: str
    expiry: str | None
    spot: float | None
    chain: pd.DataFrame
    expiries: tuple[str, ...]
    status: str
    message: str


def available_expiries(underlying: str) -> tuple[str, ...]:
    """Return provider-reported expiries, preferring NSE."""
    if underlying not in OPTIONS_UNDERLYINGS:
        raise ValueError(f"Unsupported underlying: {underlying}")

    try:
        dhan_expiries = _fetch_dhan_expiries(underlying)
        if dhan_expiries:
            return dhan_expiries
    except Exception:
        pass

    try:
        payload = _fetch_nse_option_chain(underlying)
        expiries = _nse_expiries(payload)
        if expiries:
            return expiries
    except Exception:
        pass

    symbol = OPTIONS_UNDERLYINGS[underlying]
    try:
        return tuple(str(expiry) for expiry in yf.Ticker(symbol).options)
    except Exception:
        return ()


def fetch_option_chain(
    underlying: str,
    expiry: str | None = None,
) -> OptionChainResult:
    """Fetch and normalize an Indian index option chain."""
    if underlying not in OPTIONS_UNDERLYINGS:
        raise ValueError(f"Unsupported underlying: {underlying}")

    try:
        dhan_result = _fetch_dhan_option_chain(underlying, expiry)
        if dhan_result.status == "AVAILABLE":
            return dhan_result
        dhan_error = dhan_result.message
    except Exception as exc:
        dhan_error = str(exc)

    try:
        if expiry is None:
            payload = _fetch_nse_option_chain(underlying)
        else:
            payload = _fetch_nse_option_chain(underlying, expiry)
        expiries = _nse_expiries(payload)
        if expiries:
            selected_expiry = expiry if expiry in expiries else expiries[0]
            chain = _normalize_nse_chain(payload, selected_expiry)
            spot = _nse_spot(payload)
            if not chain.empty:
                return OptionChainResult(
                    underlying,
                    f"NSE:{underlying}",
                    selected_expiry,
                    spot,
                    chain,
                    expiries,
                    "AVAILABLE",
                    "Option chain loaded from NSE fallback.",
                )
    except Exception as exc:
        nse_error = str(exc)
    else:
        nse_error = "NSE returned no usable option-chain expiries."

    yahoo_result = _fetch_yahoo_option_chain(underlying, expiry)
    if yahoo_result.status == "AVAILABLE":
        return yahoo_result

    dhan_diagnostic = f"Dhan option-chain data was unavailable ({dhan_error})"
    if "HTTP 401" in dhan_error:
        dhan_diagnostic += (
            " Dhan rejected the API credentials (HTTP 401 Unauthorized). "
            "Verify DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in the deployment secrets; "
            "if the token has expired, generate a fresh Dhan access token and update "
            "the secret before restarting the app. Never paste credentials into logs or chat."
        )
    message = (
        f"{dhan_diagnostic}; "
        f"NSE fallback was unavailable ({nse_error}); "
        f"Yahoo Finance fallback was also unavailable ({yahoo_result.message})."
    )
    return OptionChainResult(
        underlying,
        yahoo_result.provider_symbol,
        yahoo_result.expiry,
        yahoo_result.spot,
        yahoo_result.chain,
        yahoo_result.expiries,
        "UNAVAILABLE",
        message,
    )


# Streamlit reruns the whole page script on every widget click. Without a cache each
# click re-queries Dhan (which rate-limits option-chain calls) and rebuilds several NSE
# sessions. Successful chains are reused briefly; failures only very briefly so the page
# recovers quickly but a broken provider is not hammered on every rerun.
AVAILABLE_CACHE_TTL_SECONDS = 15.0
UNAVAILABLE_CACHE_TTL_SECONDS = 5.0

_chain_cache: dict[tuple[str, str | None], tuple[float, OptionChainResult]] = {}
_chain_cache_lock = threading.Lock()


def clear_option_chain_cache() -> None:
    """Drop all cached option chains (for a manual refresh button and for tests)."""
    with _chain_cache_lock:
        _chain_cache.clear()


def fetch_option_chain_cached(
    underlying: str,
    expiry: str | None = None,
    *,
    fetcher: Callable[[str, str | None], OptionChainResult] | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> OptionChainResult:
    """Return :func:`fetch_option_chain`, reusing a recent result for the same request.

    The returned chain is a copy, so callers can modify it freely.
    """
    key = (underlying, expiry)
    now = clock()
    with _chain_cache_lock:
        entry = _chain_cache.get(key)
    if entry is not None and entry[0] > now:
        return replace(entry[1], chain=entry[1].chain.copy())

    result = (fetcher or fetch_option_chain)(underlying, expiry)
    ttl = (
        AVAILABLE_CACHE_TTL_SECONDS
        if result.status == "AVAILABLE"
        else UNAVAILABLE_CACHE_TTL_SECONDS
    )
    with _chain_cache_lock:
        _chain_cache[key] = (now + ttl, result)
    return replace(result, chain=result.chain.copy())


def summarize_option_chain(chain: pd.DataFrame) -> pd.DataFrame:
    """Calculate descriptive OI and volume statistics from a normalized chain."""
    if chain.empty:
        return pd.DataFrame(columns=["Metric", "Value"])

    call_oi = pd.to_numeric(chain["CE OI"], errors="coerce").fillna(0)
    put_oi = pd.to_numeric(chain["PE OI"], errors="coerce").fillna(0)
    call_volume = pd.to_numeric(chain["CE volume"], errors="coerce").fillna(0)
    put_volume = pd.to_numeric(chain["PE volume"], errors="coerce").fillna(0)
    total_call_oi = float(call_oi.sum())
    total_put_oi = float(put_oi.sum())

    pcr = total_put_oi / total_call_oi if total_call_oi else None
    max_call = _max_oi_strike(chain, "CE OI")
    max_put = _max_oi_strike(chain, "PE OI")

    rows = [
        ("Call OI", total_call_oi),
        ("Put OI", total_put_oi),
        ("PCR (OI)", pcr),
        ("Call volume", float(call_volume.sum())),
        ("Put volume", float(put_volume.sum())),
        ("Highest Call OI strike", max_call),
        ("Highest Put OI strike", max_put),
    ]
    return pd.DataFrame(rows, columns=["Metric", "Value"])


def _dhan_expiry(value: str) -> str:
    """Convert the legacy NSE display expiry to Dhan's YYYY-MM-DD format."""
    try:
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return str(value)


def _fetch_dhan_expiries(underlying: str) -> tuple[str, ...]:
    """Return Dhan-reported expiries when Dhan credentials are configured."""
    if underlying not in DHAN_OPTION_UNDERLYINGS:
        return ()
    credentials = DhanCredentials.from_env()
    client = DhanMarketData(credentials=credentials)
    security_id, segment = DHAN_OPTION_UNDERLYINGS[underlying]
    response = client.expiry_list(security_id, segment)
    if not isinstance(response, dict) or response.get("status") != "success":
        remarks = response.get("remarks", response) if isinstance(response, dict) else response
        raise RuntimeError(f"Dhan expiry list failed: {remarks}")
    values = response.get("data", [])
    if not isinstance(values, list):
        raise RuntimeError("Dhan expiry list returned an invalid data payload.")
    return tuple(str(value) for value in values if value)


def _normalize_dhan_chain(
    payload: dict,
    underlying: str,
    expiry: str,
    expiries: tuple[str, ...],
) -> OptionChainResult:
    data = payload.get("data", {})
    if not isinstance(data, dict):
        raise RuntimeError("Dhan option-chain response has no data object.")
    raw_chain = data.get("oc", {})
    if not isinstance(raw_chain, dict):
        raise RuntimeError("Dhan option-chain response has no strike map.")

    rows = []
    for strike_text, strike_data in raw_chain.items():
        if not isinstance(strike_data, dict):
            continue
        call = strike_data.get("ce") or {}
        put = strike_data.get("pe") or {}
        if not isinstance(call, dict):
            call = {}
        if not isinstance(put, dict):
            put = {}

        def oi_change(option: dict) -> float | None:
            oi = option.get("oi")
            previous_oi = option.get("previous_oi")
            try:
                if oi is None or previous_oi is None:
                    return None
                return float(oi) - float(previous_oi)
            except (TypeError, ValueError):
                return None

        try:
            strike_price = float(strike_text)
        except (TypeError, ValueError):
            continue

        rows.append(
            {
                "strike": strike_price,
                "CE LTP": call.get("last_price"),
                "CE volume": call.get("volume"),
                "CE OI": call.get("oi"),
                "CE OI change": oi_change(call),
                "CE IV": call.get("implied_volatility"),
                "PE LTP": put.get("last_price"),
                "PE volume": put.get("volume"),
                "PE OI": put.get("oi"),
                "PE OI change": oi_change(put),
                "PE IV": put.get("implied_volatility"),
            }
        )

    chain = _finalize_chain(pd.DataFrame(rows)) if rows else pd.DataFrame(columns=CHAIN_COLUMNS)
    spot = data.get("last_price")
    try:
        spot_value = float(spot) if spot is not None else None
    except (TypeError, ValueError):
        spot_value = None

    if chain.empty:
        raise RuntimeError("Dhan returned an empty option chain.")

    return OptionChainResult(
        underlying,
        f"Dhan:{underlying}",
        expiry,
        spot_value,
        chain,
        expiries,
        "AVAILABLE",
        "Option chain loaded from Dhan.",
    )


def _fetch_dhan_option_chain(
    underlying: str,
    expiry: str | None = None,
) -> OptionChainResult:
    """Fetch an index option chain from Dhan when credentials are configured."""
    if underlying not in DHAN_OPTION_UNDERLYINGS:
        raise ValueError(f"Unsupported underlying: {underlying}")

    credentials = DhanCredentials.from_env()
    client = DhanMarketData(credentials=credentials)
    security_id, segment = DHAN_OPTION_UNDERLYINGS[underlying]

    expiry_values = _fetch_dhan_expiries(underlying)
    if not expiry_values:
        raise RuntimeError("Dhan returned no active option expiries.")

    requested = _dhan_expiry(expiry) if expiry else None
    selected = requested if requested in expiry_values else expiry_values[0]
    response = client.option_chain(security_id, segment, selected)

    if not isinstance(response, dict) or response.get("status") != "success":
        remarks = response.get("remarks", response) if isinstance(response, dict) else response
        raise RuntimeError(f"Dhan option chain failed: {remarks}")

    return _normalize_dhan_chain(response, underlying, selected, expiry_values)


def _fetch_nse_option_chain(underlying: str, expiry: str | None = None) -> dict:
    """Fetch the current NSE v3 option-chain response for one expiry."""
    try:
        expiry_values = _fetch_nse_expiries(underlying)
    except Exception:
        expiry_values = ()

    selected_expiry = expiry if expiry in expiry_values else None
    if selected_expiry is None and expiry_values:
        selected_expiry = expiry_values[0]

    session = _nse_session()
    params = {
        "type": "Indices",
        "symbol": underlying,
    }
    if selected_expiry is not None:
        params["expiry"] = selected_expiry

    try:
        response = session.get(
            NSE_OPTION_CHAIN_URL,
            params=params,
            headers=NSE_HEADERS,
            timeout=12,
        )
        if response.status_code in (401, 403, 429):
            session = _nse_session()
            response = session.get(
                NSE_OPTION_CHAIN_URL,
                params=params,
                headers=NSE_HEADERS,
                timeout=12,
            )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise RuntimeError(f"NSE v3 option-chain request failed: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("NSE v3 returned an invalid option-chain payload.")

    payload_expiries = _nse_expiries(payload)
    if not expiry_values:
        expiry_values = payload_expiries or _nse_data_expiries(payload)
    if not expiry_values:
        raise RuntimeError("NSE returned no usable option-chain expiries.")

    selected_expiry = expiry if expiry in expiry_values else expiry_values[0]
    payload.setdefault("records", {})
    if isinstance(payload["records"], dict):
        payload["records"]["expiryDates"] = list(expiry_values)
    return payload


def _fetch_nse_expiries(underlying: str) -> tuple[str, ...]:
    """Fetch current option expiries from NSE's contract-info endpoint."""
    session = _nse_session()
    try:
        response = session.get(
            NSE_OPTION_CHAIN_CONTRACT_INFO_URL,
            params={"symbol": underlying},
            headers=NSE_HEADERS,
            timeout=12,
        )
        if response.status_code in (401, 403, 429):
            session = _nse_session()
            response = session.get(
                NSE_OPTION_CHAIN_CONTRACT_INFO_URL,
                params={"symbol": underlying},
                headers=NSE_HEADERS,
                timeout=12,
            )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise RuntimeError(f"NSE expiry request failed: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("NSE expiry endpoint returned an invalid payload.")
    values = payload.get("expiryDates")
    if not isinstance(values, list):
        values = payload.get("records", {}).get("expiryDates", [])
    return tuple(str(value) for value in values if value)


def _nse_session() -> curl_requests.Session:
    """Create a browser-impersonating NSE session with fresh cookies."""
    session = curl_requests.Session(impersonate="chrome")
    session.headers.update(
        {
            **NSE_HEADERS,
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
        }
    )
    try:
        session.get(
            NSE_HOME_URL,
            headers={
                **NSE_HEADERS,
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,image/apng,*/*;q=0.8"
                ),
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
            },
            timeout=10,
        )
        session.get(
            NSE_OPTION_CHAIN_PAGE_URL,
            headers={
                **NSE_HEADERS,
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,image/apng,*/*;q=0.8"
                ),
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": "document",
            },
            timeout=10,
        )
        session.get(
            NSE_ALL_INDICES_URL,
            headers={
                **NSE_HEADERS,
                "Accept": "application/json,text/plain,*/*",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
            },
            timeout=10,
        )
    except Exception:
        # The API request remains the source of truth; some environments
        # block the NSE web pages while allowing the API endpoint.
        pass
    return session


def _nse_expiries(payload: dict) -> tuple[str, ...]:
    records = payload.get("records", {})
    values = records.get("expiryDates", [])
    return tuple(str(value) for value in values if value)


def _nse_data_expiries(payload: dict) -> tuple[str, ...]:
    """Extract unique expiry dates directly from NSE option-chain rows."""
    values = {
        str(item.get("expiryDate"))
        for item in payload.get("records", {}).get("data", [])
        if isinstance(item, dict) and item.get("expiryDate")
    }
    return tuple(sorted(values))


def _nse_spot(payload: dict) -> float | None:
    value = payload.get("records", {}).get("underlyingValue")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _normalize_nse_chain(payload: dict, expiry: str) -> pd.DataFrame:
    rows = []
    for item in payload.get("records", {}).get("data", []):
        if str(item.get("expiryDate")) != expiry:
            continue
        call = item.get("CE") or {}
        put = item.get("PE") or {}
        rows.append(
            {
                "strike": item.get("strikePrice"),
                "CE LTP": call.get("lastPrice"),
                "CE volume": call.get("totalTradedVolume"),
                "CE OI": call.get("openInterest"),
                "CE OI change": call.get("changeinOpenInterest"),
                "CE IV": call.get("impliedVolatility"),
                "PE LTP": put.get("lastPrice"),
                "PE volume": put.get("totalTradedVolume"),
                "PE OI": put.get("openInterest"),
                "PE OI change": put.get("changeinOpenInterest"),
                "PE IV": put.get("impliedVolatility"),
            }
        )

    if not rows:
        return pd.DataFrame(columns=CHAIN_COLUMNS)

    return _finalize_chain(pd.DataFrame(rows))


def _fetch_yahoo_option_chain(
    underlying: str,
    expiry: str | None,
) -> OptionChainResult:
    symbol = OPTIONS_UNDERLYINGS[underlying]
    ticker = yf.Ticker(symbol)
    try:
        expiries = tuple(str(value) for value in ticker.options)
    except Exception as exc:
        return OptionChainResult(
            underlying,
            symbol,
            expiry,
            None,
            pd.DataFrame(columns=CHAIN_COLUMNS),
            (),
            "UNAVAILABLE",
            f"Yahoo Finance expiries could not be loaded: {exc}",
        )

    if not expiries:
        return OptionChainResult(
            underlying,
            symbol,
            expiry,
            _spot_price(ticker),
            pd.DataFrame(columns=CHAIN_COLUMNS),
            (),
            "UNAVAILABLE",
            "Yahoo Finance did not expose an option chain for this underlying.",
        )

    selected_expiry = expiry if expiry in expiries else expiries[0]
    try:
        raw = ticker.option_chain(selected_expiry)
        chain = _normalize_chain(raw.calls, raw.puts)
    except Exception as exc:
        return OptionChainResult(
            underlying,
            symbol,
            selected_expiry,
            _spot_price(ticker),
            pd.DataFrame(columns=CHAIN_COLUMNS),
            expiries,
            "UNAVAILABLE",
            f"Yahoo Finance option chain could not be loaded: {exc}",
        )

    if chain.empty:
        return OptionChainResult(
            underlying,
            symbol,
            selected_expiry,
            _spot_price(ticker),
            chain,
            expiries,
            "UNAVAILABLE",
            "Yahoo Finance returned an empty option chain.",
        )

    return OptionChainResult(
        underlying,
        symbol,
        selected_expiry,
        _spot_price(ticker),
        chain,
        expiries,
        "AVAILABLE",
        "Option chain loaded from Yahoo Finance fallback.",
    )


def _normalize_chain(calls: pd.DataFrame, puts: pd.DataFrame) -> pd.DataFrame:
    call = calls.copy()
    put = puts.copy()
    for frame in (call, put):
        for column in ["strike", "lastPrice", "volume", "openInterest", "impliedVolatility"]:
            if column not in frame.columns:
                frame[column] = pd.NA

    if "changeinOpenInterest" not in call.columns:
        call["changeinOpenInterest"] = pd.NA
    if "changeinOpenInterest" not in put.columns:
        put["changeinOpenInterest"] = pd.NA

    call = call[
        [
            "strike",
            "lastPrice",
            "volume",
            "openInterest",
            "changeinOpenInterest",
            "impliedVolatility",
        ]
    ].rename(
        columns={
            "lastPrice": "CE LTP",
            "volume": "CE volume",
            "openInterest": "CE OI",
            "changeinOpenInterest": "CE OI change",
            "impliedVolatility": "CE IV",
        }
    )
    put = put[
        [
            "strike",
            "lastPrice",
            "volume",
            "openInterest",
            "changeinOpenInterest",
            "impliedVolatility",
        ]
    ].rename(
        columns={
            "lastPrice": "PE LTP",
            "volume": "PE volume",
            "openInterest": "PE OI",
            "changeinOpenInterest": "PE OI change",
            "impliedVolatility": "PE IV",
        }
    )

    chain = call.merge(put, on="strike", how="outer")
    return _finalize_chain(chain)


def _finalize_chain(chain: pd.DataFrame) -> pd.DataFrame:
    chain = chain.sort_values("strike").reset_index(drop=True)
    call_oi = pd.to_numeric(chain["CE OI"], errors="coerce")
    put_oi = pd.to_numeric(chain["PE OI"], errors="coerce")
    chain["PCR OI"] = put_oi.div(call_oi.where(call_oi.ne(0)))
    return chain[CHAIN_COLUMNS]


def _max_oi_strike(chain: pd.DataFrame, column: str) -> float | None:
    values = pd.to_numeric(chain[column], errors="coerce")
    if values.dropna().empty:
        return None
    return float(chain.loc[values.idxmax(), "strike"])


def _spot_price(ticker: yf.Ticker) -> float | None:
    try:
        history = ticker.history(period="1d", interval="1m")
        if history.empty:
            return None
        return float(history["Close"].dropna().iloc[-1])
    except Exception:
        return None
