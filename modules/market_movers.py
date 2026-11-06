"""NSE+BSE intraday market-movers board with explicit coverage and data-quality labels."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from time import perf_counter
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import yfinance as yf

from scanner.dynamic_universe import merge_bse_universe, merge_nse_universe
from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES
from services.symbol_resolver import yahoo_ticker

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")
BATCH_SIZE = 40
CAP_WORKERS = 12
CAP_CACHE_TTL_SECONDS = 1800
SCAN_CACHE_TTL_SECONDS = 180
LARGE_CAP_RANK_MAX = 100
MID_CAP_RANK_MAX = 250


def _ticker(symbol: str, exchange: str) -> str:
    cleaned = str(symbol).strip().upper()
    suffix = ".NS" if exchange == "NSE" else ".BO"
    return yahoo_ticker(cleaned if cleaned.endswith((".NS", ".BO")) else f"{cleaned}{suffix}")


def _extract_frame(history: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Extract OHLCV for one ticker from either yfinance MultiIndex orientation."""
    if history is None or history.empty:
        return pd.DataFrame()
    if not isinstance(history.columns, pd.MultiIndex):
        frame = history.copy()
    else:
        frame = pd.DataFrame()
        for level in range(history.columns.nlevels):
            if ticker in history.columns.get_level_values(level):
                frame = history.xs(ticker, axis=1, level=level).copy()
                break
    required = {"Open", "High", "Low", "Close", "Volume"}
    if frame.empty or not required.issubset(frame.columns):
        return pd.DataFrame()
    frame = frame.loc[:, list(required)].apply(pd.to_numeric, errors="coerce")
    frame = frame.dropna(subset=["Close"]).sort_index()
    return frame.loc[~frame.index.duplicated(keep="last")]


def _window_change(close: pd.Series, bars: int) -> float | None:
    """Calculate return over N five-minute bars, requiring a complete baseline."""
    values = pd.to_numeric(close, errors="coerce").dropna()
    if len(values) <= bars or float(values.iloc[-bars - 1]) <= 0:
        return None
    return round((float(values.iloc[-1]) / float(values.iloc[-bars - 1]) - 1) * 100, 3)


def _market_cap(ticker: str) -> float | None:
    try:
        value = yf.Ticker(ticker).fast_info.get("market_cap")
        number = float(value) if value is not None else 0.0
        return number if number > 0 else None
    except Exception as exc:
        logger.debug("Market cap lookup failed for %s: %s", ticker, exc)
        return None


def _scan_batches(
    candidates: list[tuple[str, str]], limit_per_exchange: int
) -> tuple[pd.DataFrame, dict[str, int | float | str]]:
    """Scan 5-minute candles in batches and return coverage diagnostics."""
    selected: list[tuple[str, str]] = []
    for exchange in ("NSE", "BSE"):
        exchange_candidates = [item for item in candidates if item[1] == exchange]
        selected.extend(
            exchange_candidates[:limit_per_exchange] if limit_per_exchange else exchange_candidates
        )

    rows: list[dict[str, object]] = []
    failed_batches = 0
    batches = 0
    started = perf_counter()
    for exchange in ("NSE", "BSE"):
        exchange_items = [item for item in selected if item[1] == exchange]
        tickers = [_ticker(symbol, exchange) for symbol, _ in exchange_items]
        symbol_by_ticker = {_ticker(symbol, exchange): symbol for symbol, _ in exchange_items}
        for start in range(0, len(tickers), BATCH_SIZE):
            chunk = tickers[start : start + BATCH_SIZE]
            batches += 1
            try:
                history = yf.download(
                    tickers=chunk,
                    period="5d",
                    interval="5m",
                    auto_adjust=False,
                    progress=False,
                    group_by="ticker",
                    threads=False,
                    timeout=15,
                )
            except Exception:
                failed_batches += 1
                continue
            for ticker in chunk:
                frame = _extract_frame(history, ticker)
                if len(frame) < 7:
                    continue
                close = pd.to_numeric(frame["Close"], errors="coerce").dropna()
                volume = pd.to_numeric(frame["Volume"], errors="coerce").fillna(0)
                if len(close) < 7 or float(close.iloc[-1]) <= 0:
                    continue
                symbol = symbol_by_ticker.get(ticker, ticker.rsplit(".", 1)[0])
                latest_time = frame.index[-1]
                try:
                    observed = pd.Timestamp(latest_time)
                    if observed.tzinfo is None:
                        observed = observed.tz_localize("UTC")
                    observed_at = observed.tz_convert(IST).strftime("%Y-%m-%d %H:%M:%S IST")
                except (TypeError, ValueError):
                    observed_at = str(latest_time)
                last_volume = float(volume.iloc[-1]) if len(volume) else 0.0
                baseline = (
                    float(volume.iloc[-21:-1].median())
                    if len(volume) >= 21
                    else (float(volume.iloc[:-1].median()) if len(volume) > 1 else 0.0)
                )
                volume_ratio = round(last_volume / baseline, 2) if baseline > 0 else None
                high_window = pd.to_numeric(frame["High"], errors="coerce").dropna().tail(13)
                breakout = bool(
                    len(high_window) >= 13
                    and float(close.iloc[-1]) > float(high_window.iloc[:-1].max())
                )
                rows.append(
                    {
                        "Symbol": symbol,
                        "Ticker": ticker,
                        "Exchange": exchange,
                        "Price": round(float(close.iloc[-1]), 2),
                        "Change 5m %": _window_change(close, 1),
                        "Change 15m %": _window_change(close, 3),
                        "Change 30m %": _window_change(close, 6),
                        "Volume": int(last_volume),
                        "Volume surge x": volume_ratio,
                        "Breakout (65m)": breakout,
                        "Observed (IST)": observed_at,
                        "Market cap (₹)": None,
                        "Market-cap class": "Unverified",
                    }
                )

    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.drop_duplicates(subset=["Ticker"], keep="last").reset_index(drop=True)
    stats: dict[str, int | float | str] = {
        "candidate_count": len(selected),
        "limit_per_exchange": limit_per_exchange,
        "usable_quotes": len(frame),
        "failed_batches": failed_batches,
        "batches": batches,
        "elapsed_seconds": round(perf_counter() - started, 1),
        "scan_completed_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
        "nse_candidates": sum(exchange == "NSE" for _, exchange in selected),
        "bse_candidates": sum(exchange == "BSE" for _, exchange in selected),
    }
    return frame, stats


def _classify_market_caps(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach estimated cap ranks; these are not official AMFI category labels."""
    result = frame.copy()
    if result.empty:
        return result
    candidates = result.sort_values(
        "Change 30m %", key=lambda values: values.abs(), ascending=False
    )
    # Metadata lookups are limited to the strongest 300 observed movers to bound latency.
    tickers = candidates["Ticker"].head(300).dropna().astype(str).unique().tolist()
    cap_by_ticker: dict[str, float | None] = {}
    with ThreadPoolExecutor(max_workers=CAP_WORKERS) as executor:
        futures = {executor.submit(_market_cap, ticker): ticker for ticker in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                cap_by_ticker[ticker] = future.result()
            except Exception:
                cap_by_ticker[ticker] = None
    result["Market cap (₹)"] = result["Ticker"].map(cap_by_ticker)
    known = result.dropna(subset=["Market cap (₹)"]).sort_values("Market cap (₹)", ascending=False)
    for rank, index in enumerate(known.index, start=1):
        if rank <= LARGE_CAP_RANK_MAX:
            result.loc[index, "Market-cap class"] = "Large-cap (estimated rank)"
        elif rank <= MID_CAP_RANK_MAX:
            result.loc[index, "Market-cap class"] = "Mid-cap (estimated rank)"
        else:
            result.loc[index, "Market-cap class"] = "Small-cap (estimated rank)"
    return result


@st.cache_data(ttl=SCAN_CACHE_TTL_SECONDS, show_spinner=False)
def _cached_scan(limit_per_exchange: int) -> tuple[pd.DataFrame, dict[str, int | float | str]]:
    nse = merge_nse_universe()
    bse = merge_bse_universe()
    nse_ordered = list(dict.fromkeys(NSE_CANDIDATES + nse))
    bse_ordered = list(dict.fromkeys(BSE_CANDIDATES + bse))
    candidates = [(symbol, "NSE") for symbol in nse_ordered] + [
        (symbol, "BSE") for symbol in bse_ordered
    ]
    frame, stats = _scan_batches(candidates, limit_per_exchange)
    frame = _classify_market_caps(frame)
    stats["market_cap_lookups"] = min(300, len(frame))
    stats["market_cap_verified"] = (
        int(frame["Market cap (₹)"].notna().sum()) if not frame.empty else 0
    )
    stats["nse_universe_available"] = len(nse)
    stats["bse_universe_available"] = len(bse)
    stats["coverage_note"] = (
        "Universe is sourced from dynamic exchange lists with curated fallback. "
        "The selected scan limit may exclude symbols; quote failures are counted as unavailable. "
        "Cap classes are estimated by market-cap rank among the metadata-verified scan shortlist, "
        "not official AMFI classifications. Yahoo Finance data is not exchange-tick real time."
    )
    return frame, stats


def _top_table(frame: pd.DataFrame, change_column: str, positive: bool, count: int) -> pd.DataFrame:
    if frame.empty or change_column not in frame:
        return pd.DataFrame()
    values = pd.to_numeric(frame[change_column], errors="coerce")
    filtered = frame.loc[values > 0] if positive else frame.loc[values < 0]
    return (
        filtered.sort_values(change_column, ascending=not positive)
        .head(count)
        .reset_index(drop=True)
    )


def show() -> None:
    st.title("⚡ Intraday Market Movers")
    st.caption(
        "NSE + BSE · Large, mid and small-cap discovery · 5/15/30-minute momentum · "
        "volume surge and breakout screening"
    )
    st.warning(
        "Yahoo Finance intraday observations are not guaranteed real-time exchange data. "
        "Use this as a research scanner, not an automatic trade instruction."
    )

    with st.expander("Scanner coverage and filters", expanded=True):
        limit_label = st.selectbox(
            "Symbols to scan per exchange",
            ["250 (faster)", "500", "1,000", "All available"],
            index=0,
            help="The dynamic exchange universe can contain thousands of securities. "
            "Choose All available for the broadest scan; it can take several minutes.",
        )
        limit = {"250 (faster)": 250, "500": 500, "1,000": 1000, "All available": 0}[limit_label]
        exchange_filter = st.selectbox("Exchange", ["NSE + BSE", "NSE", "BSE"])
        cap_filter = st.selectbox(
            "Market-cap class",
            [
                "All",
                "Large-cap (estimated rank)",
                "Mid-cap (estimated rank)",
                "Small-cap (estimated rank)",
                "Unverified",
            ],
        )
        mover_window = st.selectbox(
            "Rank by movement", ["Change 5m %", "Change 15m %", "Change 30m %"]
        )
        count = st.selectbox("Rows per leaderboard", [10, 20, 50], index=0)

    if st.button("Scan / refresh market movers", type="primary", use_container_width=True):
        _cached_scan.clear()
        with st.spinner(
            "Loading dynamic NSE/BSE universe and scanning intraday candles. "
            "Full scans may take several minutes…"
        ):
            st.session_state["market_movers_result"] = _cached_scan(limit)

    if "market_movers_result" not in st.session_state:
        st.info(
            "Choose scan coverage, then click **Scan / refresh market movers** "
            "to fetch the latest available candles."
        )
        return
    frame, stats = st.session_state["market_movers_result"]
    if stats.get("limit_per_exchange") != limit:
        st.info(
            "The selected scan coverage differs from the last result. "
            "Click **Scan / refresh market movers** to rescan."
        )

    if frame.empty:
        st.error(
            "No usable intraday quotes were returned. "
            "Try again during market hours or reduce scan size."
        )
        st.json(stats)
        return

    if exchange_filter != "NSE + BSE":
        frame = frame.loc[frame["Exchange"] == exchange_filter]
    if cap_filter != "All":
        frame = frame.loc[frame["Market-cap class"] == cap_filter]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Symbols requested", int(stats["candidate_count"]))
    c2.metric("Usable quotes", int(stats["usable_quotes"]))
    c3.metric("Market-cap verified", int(stats["market_cap_verified"]))
    c4.metric("Failed batches", int(stats["failed_batches"]))
    st.caption(
        f"Scan completed {stats['scan_completed_at']} · {stats['elapsed_seconds']} s · "
        f"Dynamic universe: NSE {stats['nse_universe_available']}, "
        f"BSE {stats['bse_universe_available']}. "
        f"Scanned NSE {stats['nse_candidates']} and BSE {stats['bse_candidates']} symbols."
    )
    st.info(str(stats["coverage_note"]))

    st.subheader(f"Top gainers — {mover_window}")
    st.dataframe(
        _top_table(frame, mover_window, True, count),
        hide_index=True,
        use_container_width=True,
    )
    st.subheader(f"Top losers — {mover_window}")
    st.dataframe(
        _top_table(frame, mover_window, False, count),
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("Top movers by market-cap class")
    class_col1, class_col2, class_col3 = st.columns(3)
    for column, cap_class in (
        (class_col1, "Large-cap (estimated rank)"),
        (class_col2, "Mid-cap (estimated rank)"),
        (class_col3, "Small-cap (estimated rank)"),
    ):
        with column:
            st.markdown(f"**{cap_class}**")
            class_frame = frame.loc[frame["Market-cap class"] == cap_class]
            st.dataframe(
                _top_table(class_frame, mover_window, True, min(count, 10)),
                hide_index=True,
                use_container_width=True,
            )

    st.subheader("Volume surges and breakouts")
    signal_frame = frame.loc[
        (pd.to_numeric(frame["Volume surge x"], errors="coerce") >= 2)
        | frame["Breakout (65m)"].fillna(False).astype(bool)
    ].sort_values(mover_window, ascending=False)
    st.dataframe(signal_frame.head(50), hide_index=True, use_container_width=True)
    st.download_button(
        "Download scanned results (CSV)",
        frame.to_csv(index=False),
        "intraday_market_movers.csv",
        "text/csv",
    )
