"""Canonical boundary for externally sourced market observations."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

from services.resilient_market_data import download_symbol_frames

logger = logging.getLogger(__name__)

MARKET_INDICES = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANK NIFTY": "^NSEBANK",
    "INDIA VIX": "^INDIAVIX",
    "USD/INR": "INR=X",
    "GOLD": "GC=F",
}

WATCHLIST = {
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "SBIN": "SBIN.NS",
    "LT": "LT.NS",
    "ITC": "ITC.NS",
    "BHARTIARTL": "BHARTIARTL.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
}

EXCHANGE_SUFFIXES = {
    "NSE": ".NS",
    "BSE": ".BO",
}

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)
MARKET_INDEX_WORKERS = 6


def normalize_market_symbol(symbol: str, exchange: str = "NSE") -> str:
    """Normalize an Indian equity symbol to a Yahoo Finance ticker."""
    normalized = symbol.strip().upper()
    if not normalized:
        return ""

    requested_exchange = exchange.strip().upper()
    if requested_exchange not in EXCHANGE_SUFFIXES:
        raise ValueError("exchange must be NSE or BSE")

    # An explicit Yahoo Finance suffix is authoritative and must be preserved.
    if normalized.endswith((".NS", ".BO")):
        return normalized

    return f"{normalized}{EXCHANGE_SUFFIXES[requested_exchange]}"


def market_session_status(
    observed_at: str | None,
    frequency: str = "unknown",
    now: datetime | None = None,
) -> dict[str, str | bool | None]:
    """Describe whether the displayed observation is current for India."""
    current = now.astimezone(INDIA_TIMEZONE) if now else datetime.now(INDIA_TIMEZONE)

    if not observed_at:
        return {
            "status": "DATA UNAVAILABLE",
            "detail": "No observation timestamp is available.",
            "is_current_session": False,
            "is_market_open": MARKET_OPEN <= current.time() < MARKET_CLOSE,
        }

    try:
        observed = pd.Timestamp(observed_at)
        if observed.tzinfo is None:
            observed = observed.tz_localize(INDIA_TIMEZONE)
        else:
            observed = observed.tz_convert(INDIA_TIMEZONE)
        observed_dt = observed.to_pydatetime()
    except (TypeError, ValueError):
        return {
            "status": "DATA TIMESTAMP UNAVAILABLE",
            "detail": "The latest observation timestamp could not be parsed.",
            "is_current_session": False,
            "is_market_open": False,
        }

    if (observed_dt - current).total_seconds() > 5 * 60:
        return {
            "status": "FUTURE-DATED MARKET DATA",
            "detail": (
                "The observation timestamp is more than 5 minutes ahead of the current time; "
                "do not treat this quote as current. "
                f"Reported observation: {observed_dt.strftime('%d %b %Y %H:%M:%S IST')}"
            ),
            "is_current_session": False,
            "is_market_open": MARKET_OPEN <= current.time() < MARKET_CLOSE
            and current.weekday() < 5,
        }

    same_day = observed_dt.date() == current.date()
    weekend = current.weekday() >= 5
    market_open = MARKET_OPEN <= current.time() < MARKET_CLOSE
    intraday = frequency.startswith("intraday")

    if weekend:
        status = "MARKET CLOSED · WEEKEND"
        detail = f"Last available data: {observed_dt.strftime('%d %b %Y %H:%M IST')}"
        current_session = False
    elif not same_day:
        status = "MARKET CLOSED · LAST SESSION"
        detail = f"Last session data: {observed_dt.strftime('%d %b %Y %H:%M IST')}"
        current_session = False
    elif market_open and intraday and (current - observed_dt).total_seconds() > 15 * 60:
        status = "STALE INTRADAY DATA"
        detail = (
            "Latest candle is more than 15 minutes old; do not treat this quote as current. "
            f"Last observation: {observed_dt.strftime('%d %b %Y %H:%M:%S IST')}"
        )
        current_session = False
    elif market_open and intraday:
        status = "INTRADAY DATA · TODAY"
        detail = (
            "Yahoo Finance intraday observation; not exchange-tick live. "
            f"Latest candle: {observed_dt.strftime('%H:%M:%S IST')}"
        )
        current_session = True
    elif market_open and not intraday:
        status = "DAILY DATA ONLY · INTRADAY UNAVAILABLE"
        detail = (
            "Only daily-frequency data is available during market hours; "
            "it must not be presented as a current intraday quote. "
            f"Latest daily observation: {observed_dt.strftime('%d %b %Y %H:%M IST')}"
        )
        current_session = False
    elif current.time() < MARKET_OPEN:
        status = "PRE-MARKET"
        detail = f"Latest available data: {observed_dt.strftime('%d %b %Y %H:%M IST')}"
        current_session = False
    else:
        status = "MARKET CLOSED · TODAY'S DATA"
        detail = f"Latest session data: {observed_dt.strftime('%d %b %Y %H:%M IST')}"
        current_session = same_day

    return {
        "status": status,
        "detail": detail,
        "is_current_session": current_session,
        "is_market_open": market_open and not weekend,
    }


def get_company_name(ticker: str) -> str:
    """Resolve a human-readable company name, with Yahoo search as fallback."""
    try:
        info = yf.Ticker(ticker).get_info()
        name = info.get("longName") or info.get("shortName")
        if isinstance(name, str) and name.strip():
            return name.strip()
    except Exception as exc:
        logger.debug("Company name lookup failed for %s: %s", ticker, exc)

    try:
        quotes = yf.Search(ticker, max_results=8, news_count=0).quotes
        normalized = ticker.strip().upper()
        for quote in quotes:
            symbol = str(quote.get("symbol", "")).strip().upper()
            if symbol != normalized:
                continue
            name = quote.get("longname") or quote.get("shortname")
            if isinstance(name, str) and name.strip():
                return name.strip()
        for quote in quotes:
            name = quote.get("longname") or quote.get("shortname")
            if isinstance(name, str) and name.strip():
                return name.strip()
    except Exception as exc:
        logger.debug("Symbol search failed for %s: %s", ticker, exc)

    return ticker


def _clean_close_series(history: pd.DataFrame) -> pd.Series:
    if history is None or history.empty or "Close" not in history:
        return pd.Series(dtype="float64")
    close = history["Close"]
    if isinstance(close, pd.DataFrame):
        if close.shape[1] != 1:
            return pd.Series(dtype="float64")
        close = close.iloc[:, 0]
    return pd.to_numeric(close, errors="coerce").dropna()


def _get_last_observation(
    ticker: str,
) -> tuple[float | None, float | None, float | None, str | None, str, bool]:
    """Return price, change, previous close, time, frequency and intraday flag."""
    try:
        intraday_frames, _intraday_diagnostics = download_symbol_frames(
            [ticker],
            period="1d",
            interval="1m",
            auto_adjust=True,
            batch_size=1,
            timeout=15,
        )
        close = _clean_close_series(intraday_frames.get(ticker, pd.DataFrame()))
        if not close.empty:
            latest = float(close.iloc[-1])
            previous = None
            daily_frames, _daily_diagnostics = download_symbol_frames(
                [ticker],
                period="5d",
                interval="1d",
                auto_adjust=True,
                batch_size=1,
                timeout=15,
            )
            daily_close = _clean_close_series(daily_frames.get(ticker, pd.DataFrame()))
            if len(daily_close) >= 2:
                previous = float(daily_close.iloc[-2])
            elif len(daily_close) == 1:
                previous = float(daily_close.iloc[-1])
            if previous is None and len(close) > 1:
                previous = float(close.iloc[-2])
            change = ((latest - previous) / previous) * 100 if previous else None
            timestamp = close.index[-1]
            observed_at = (
                timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
            )
            return (
                round(latest, 2),
                round(change, 2) if change is not None else None,
                round(previous, 2) if previous is not None else None,
                observed_at,
                "intraday_1m",
                True,
            )

        daily_frames, _daily_diagnostics = download_symbol_frames(
            [ticker],
            period="5d",
            interval="1d",
            auto_adjust=True,
            batch_size=1,
            timeout=15,
        )
        close = _clean_close_series(daily_frames.get(ticker, pd.DataFrame()))
        if close.empty:
            return None, None, None, None, "unavailable", False
        latest = float(close.iloc[-1])
        previous = float(close.iloc[-2]) if len(close) > 1 else None
        change = ((latest - previous) / previous) * 100 if previous else None
        timestamp = close.index[-1]
        observed_at = timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
        return (
            round(latest, 2),
            round(change, 2) if change is not None else None,
            round(previous, 2) if previous is not None else None,
            observed_at,
            "daily",
            False,
        )
    except Exception:
        return None, None, None, None, "unavailable", False


def get_latest_available_price(symbol: str, exchange: str = "NSE") -> dict[str, Any]:
    """Fetch a quote only from the requested exchange; never substitute another listing."""
    normalized = normalize_market_symbol(symbol, exchange)
    value, change, previous_close, observed_at, frequency, is_intraday = _get_last_observation(
        normalized
    )
    resolved_exchange = "BSE" if normalized.endswith(".BO") else "NSE"
    session = market_session_status(observed_at, frequency)
    return {
        "symbol": normalized,
        "provider_symbol": normalized,
        "exchange": resolved_exchange,
        "price": value,
        "previous_close": previous_close,
        "change_pct": change,
        "observed_at": observed_at,
        "source": "Yahoo Finance",
        "frequency": frequency,
        "is_tick_live": False,
        "is_intraday": is_intraday,
        "session_status": session["status"],
        "session_detail": session["detail"],
        "is_current_session": session["is_current_session"],
        "is_market_open": session["is_market_open"],
    }


def get_market_indices() -> dict[str, dict[str, Any]]:
    """Return market indices concurrently so slow provider calls do not serialize startup."""

    def fetch(item: tuple[str, str]) -> tuple[str, dict[str, Any]]:
        name, ticker = item
        value, change, _previous_close, observed_at, frequency, is_intraday = _get_last_observation(
            ticker
        )
        session = market_session_status(observed_at, frequency)
        return name, {
            "value": value,
            "change": change,
            "observed_at": observed_at,
            "source": "Yahoo Finance",
            "frequency": frequency,
            "is_tick_live": False,
            "is_intraday": is_intraday,
            "session_status": session["status"],
            "session_detail": session["detail"],
            "is_current_session": session["is_current_session"],
            "is_market_open": session["is_market_open"],
        }

    with ThreadPoolExecutor(max_workers=MARKET_INDEX_WORKERS) as executor:
        return dict(executor.map(fetch, MARKET_INDICES.items()))


def _scan_watchlist(watchlist: dict[str, str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name, ticker in watchlist.items():
        value, change, _previous_close, observed_at, frequency, is_intraday = _get_last_observation(
            ticker
        )
        if value is None or change is None:
            continue
        exchange = "BSE" if ticker.endswith(".BO") else "NSE"
        session = market_session_status(observed_at, frequency)
        rows.append(
            {
                "Symbol": name,
                "Name": get_company_name(ticker),
                "Exchange": exchange,
                "Ticker": ticker,
                "Price": value,
                "Change %": change,
                "Observed": observed_at,
                "Frequency": frequency,
                "Intraday": is_intraday,
                "Session Status": session["status"],
                "Session Detail": session["detail"],
                "Current Session": session["is_current_session"],
                "Market Open": session["is_market_open"],
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "Symbol",
            "Name",
            "Exchange",
            "Ticker",
            "Price",
            "Change %",
            "Observed",
            "Frequency",
            "Intraday",
            "Session Status",
            "Session Detail",
            "Current Session",
            "Market Open",
        ],
    )


def get_top_movers(
    watchlist: dict[str, str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return top gainers and losers from the supplied NSE/BSE universe."""
    frame = _scan_watchlist(watchlist or WATCHLIST)
    if frame.empty:
        return frame.copy(), frame.copy()
    return (
        frame.sort_values("Change %", ascending=False).head(5).reset_index(drop=True),
        frame.sort_values("Change %", ascending=True).head(5).reset_index(drop=True),
    )


def scan_market_universe(
    symbols_by_exchange: dict[str, list[str]],
    top_n: int = 10,
) -> pd.DataFrame:
    """Scan an explicit NSE/BSE universe and return the largest movers."""
    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    rows: list[dict[str, Any]] = []
    for exchange, symbols in symbols_by_exchange.items():
        for symbol in symbols:
            normalized = normalize_market_symbol(symbol, exchange)
            quote = get_latest_available_price(normalized, exchange)
            if quote.get("price") is None or quote.get("change_pct") is None:
                continue
            rows.append(
                {
                    "Symbol": normalized.removesuffix(".NS").removesuffix(".BO"),
                    "Name": "",
                    "Exchange": quote["exchange"],
                    "Ticker": normalized,
                    "Price": quote["price"],
                    "Change %": quote["change_pct"],
                    "Observed": quote["observed_at"],
                    "Frequency": quote["frequency"],
                    "Intraday": quote["is_intraday"],
                    "Session Status": quote.get("session_status", "UNKNOWN"),
                    "Session Detail": quote.get("session_detail", ""),
                    "Current Session": quote.get("is_current_session", False),
                    "Market Open": quote.get("is_market_open", False),
                }
            )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["Absolute Change %"] = frame["Change %"].abs()
    result = (
        frame.sort_values(["Absolute Change %", "Change %"], ascending=[False, False])
        .head(top_n)
        .drop(columns=["Absolute Change %"])
        .reset_index(drop=True)
    )
    result["Name"] = [get_company_name(ticker) for ticker in result["Ticker"]]
    return result
