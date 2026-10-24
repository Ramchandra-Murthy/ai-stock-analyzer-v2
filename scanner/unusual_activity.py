from __future__ import annotations

from typing import Any

import pandas as pd

from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES, bse_candidates_for_nse_symbols
from services.resilient_market_data import download_market_frames

CHUNK_SIZE = 100

# Representative NSE candidate baskets, not exhaustive exchange classifications.
# Categories are based on widely followed index constituents; market-cap ranks can change.
CAP_UNIVERSES = {
    "Large cap": {
        "RELIANCE",
        "TCS",
        "INFY",
        "HDFCBANK",
        "ICICIBANK",
        "SBIN",
        "LT",
        "ITC",
        "BHARTIARTL",
        "HINDUNILVR",
        "KOTAKBANK",
        "AXISBANK",
        "MARUTI",
        "M&M",
        "TITAN",
        "SUNPHARMA",
        "ADANIENT",
        "ADANIPORTS",
        "HCLTECH",
        "WIPRO",
        "ULTRACEMCO",
        "NTPC",
        "POWERGRID",
        "ONGC",
        "COALINDIA",
        "TATASTEEL",
        "JSWSTEEL",
        "BAJFINANCE",
        "BAJAJFINSV",
        "ASIANPAINT",
        "NESTLEIND",
        "TECHM",
        "TATAMOTORS",
        "TATACONSUM",
        "CIPLA",
        "DRREDDY",
        "DIVISLAB",
        "APOLLOHOSP",
        "GRASIM",
        "EICHERMOT",
        "HEROMOTOCO",
        "BAJAJ-AUTO",
        "BRITANNIA",
        "HINDALCO",
        "BPCL",
        "IOC",
        "GAIL",
        "INDUSINDBK",
        "BANKBARODA",
        "CANBK",
        "IDFCFIRSTB",
        "PNB",
        "DLF",
        "BEL",
        "HAL",
        "DMART",
        "TRENT",
        "SIEMENS",
        "ABB",
        "VEDL",
        "HAVELLS",
        "DABUR",
        "GODREJCP",
        "PIDILITIND",
        "COLPAL",
        "MOTHERSON",
        "TVSMOTOR",
        "INDIGO",
        "ICICIGI",
        "SBILIFE",
        "HDFCLIFE",
        "LICI",
    },
    "Mid cap": {
        "IRFC",
        "RVNL",
        "ZOMATO",
        "NYKAA",
        "PAYTM",
        "JIOFIN",
        "ASHOKLEY",
        "LODHA",
        "BHEL",
        "POLICYBZR",
        "PERSISTENT",
        "COFORGE",
        "MPHASIS",
        "LTIM",
        "AUROPHARMA",
        "LUPIN",
        "TORNTPHARM",
        "BOSCHLTD",
        "INDUSTOWER",
        "NAUKRI",
        "CHOLAFIN",
        "HINDPETRO",
        "UNIONBANK",
        "FEDERALBNK",
        "IDBI",
        "CUMMINSIND",
        "MAXHEALTH",
        "FORTIS",
        "PAGEIND",
    },
    "Small cap": {
        "CESC",
        "YESBANK",
        "IDFC",
        "RBLBANK",
        "BANDHANBNK",
        "CANFINHOME",
        "SUZLON",
        "NHPC",
        "SJVN",
        "IREDA",
        "NBCC",
        "HUDCO",
        "IRCON",
        "RITES",
        "KALYANKJIL",
        "DELHIVERY",
        "CROMPTON",
        "VOLTAS",
        "BATAINDIA",
        "ZEEL",
        "SAIL",
        "NMDC",
        "NATIONALUM",
        "JINDALSTEL",
        "MANAPPURAM",
        "MUTHOOTFIN",
        "ANGELONE",
        "BSE",
        "CAMS",
        "HFCL",
        "INOXWIND",
    },
}


def _ticker(symbol: str, exchange: str) -> str:
    return f"{symbol}.{ 'NS' if exchange == 'NSE' else 'BO'}"


def _frame_for(history: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if isinstance(history.columns, pd.MultiIndex):
        if ticker not in history.columns.get_level_values(0):
            return pd.DataFrame()
        frame = history[ticker].copy()
    else:
        frame = history.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    return frame


def finalize_scan_result(
    rows: list[dict[str, Any]],
    limit: int,
    sort_columns: list[str],
    stats: dict[str, Any],
) -> pd.DataFrame:
    """Build, rank, and annotate a scanner result consistently."""
    stats["matches_before_limit"] = len(rows)
    if not rows:
        result = pd.DataFrame()
    else:
        result = (
            pd.DataFrame(rows)
            .sort_values(sort_columns, ascending=[False] * len(sort_columns), na_position="last")
            .head(max(1, min(int(limit), 100)))
            .reset_index(drop=True)
        )
    stats["displayed_count"] = len(result)
    result.attrs["scan_stats"] = stats
    return result


def scan_unusual_activity(
    limit: int = 20,
    cap_category: str = "All caps",
    exchange_category: str = "Both",
) -> pd.DataFrame:
    """Find positive intraday movers with unusually high latest-bar volume.

    Uses Yahoo Finance 5-minute candles and representative candidate baskets.
    BSE numeric scrip-code candidates are included only in All caps because this
    repository does not maintain a verified cap-category mapping for those codes.
    """
    rows: list[dict[str, Any]] = []
    exchanges = ("NSE", "BSE") if exchange_category == "Both" else (exchange_category,)
    if cap_category == "All caps":
        universe = [(symbol, "NSE") for symbol in NSE_CANDIDATES] + [
            (symbol, "BSE") for symbol in BSE_CANDIDATES
        ]
    else:
        selected = CAP_UNIVERSES.get(cap_category, set())
        universe = [(symbol, "NSE") for symbol in NSE_CANDIDATES if symbol in selected]
        universe.extend((symbol, "BSE") for symbol in bse_candidates_for_nse_symbols(selected))

    selected_universe = [(symbol, venue) for symbol, venue in universe if venue in exchanges]
    stats = {
        "candidate_count": len(selected_universe),
        "attempted_count": 0,
        "usable_count": 0,
        "download_failed_chunks": 0,
        "empty_chunks": 0,
        "processing_errors": 0,
        "matches_before_limit": 0,
        "displayed_count": 0,
    }
    for exchange in exchanges:
        symbols = [symbol for symbol, venue in selected_universe if venue == exchange]
        tickers = [_ticker(symbol, exchange) for symbol in symbols]
        for start in range(0, len(tickers), CHUNK_SIZE):
            chunk = tickers[start : start + CHUNK_SIZE]
            stats["attempted_count"] += len(chunk)
            frames, diagnostics = download_market_frames(
                chunk,
                period="5d",
                interval="5m",
                batch_size=100,
                timeout=5,
                retries=0,
                recover_missing=False,
            )
            stats["download_failed_chunks"] += int(bool(diagnostics["missing"]))
            if not frames:
                stats["empty_chunks"] += 1
                continue
            for ticker in chunk:
                try:
                    frame = frames.get(ticker, pd.DataFrame())
                    required = {"Open", "High", "Low", "Close", "Volume"}
                    if frame.empty or not required.issubset(frame.columns):
                        continue
                    frame = frame.dropna(subset=list(required)).sort_index()
                    frame = frame[~frame.index.duplicated(keep="last")]
                    if frame.empty:
                        continue
                    stats["usable_count"] += 1
                    if len(frame) < 3:
                        continue
                    dates = pd.Series(frame.index.date, index=frame.index)
                    session_date = dates.iloc[-1]
                    current = frame.loc[dates == session_date]
                    previous = frame.loc[dates != session_date]
                    if current.empty or previous.empty:
                        continue
                    latest = current.iloc[-1]
                    opening_price = float(current.iloc[0]["Open"])
                    price = float(latest["Close"])
                    if opening_price <= 0 or price <= opening_price:
                        continue
                    clock = pd.Timestamp(current.index[-1]).strftime("%H:%M")
                    same_time = previous.loc[previous.index.strftime("%H:%M") == clock, "Volume"]
                    baseline = (
                        float(same_time.tail(4).mean()) if not same_time.empty else float("nan")
                    )
                    volume = float(latest["Volume"])
                    if pd.isna(baseline) or baseline <= 0:
                        continue
                    relative_volume = volume / baseline
                    if relative_volume < 1.5:
                        continue
                    rows.append(
                        {
                            "Symbol": ticker.rsplit(".", 1)[0],
                            "Exchange": exchange,
                            "Market-cap basket": cap_category,
                            "Last price": round(price, 2),
                            "Session change %": round((price / opening_price - 1) * 100, 2),
                            "Latest bar volume": int(volume),
                            "Relative volume": round(relative_volume, 2),
                            "Latest candle (provider time)": str(current.index[-1]),
                        }
                    )
                except (KeyError, TypeError, ValueError, IndexError):
                    stats["processing_errors"] += 1
                    continue
    return finalize_scan_result(
        rows,
        limit,
        ["Relative volume", "Session change %"],
        stats,
    )
