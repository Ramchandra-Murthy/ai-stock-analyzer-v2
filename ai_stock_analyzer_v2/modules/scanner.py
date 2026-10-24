"""Streamlit UI for broad-market and personal-watchlist AI scanning."""

import math

import pandas as pd
import streamlit as st

from scanner.market_scanner import DISPLAY_COUNT, market_scan
from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES
from scanner.watchlist_scanner import scan_watchlist
from services.market_service import WATCHLIST
from services.watchlist_service import WatchlistError
from services.watchlist_ui import get_or_create_default_watchlist


def _show_data_quality(df: pd.DataFrame) -> None:
    """Show transparent checks for the rows returned by the scanner."""
    st.subheader("Data quality")
    required = [column for column in ("Symbol", "Price", "RSI", "AI Score") if column in df.columns]
    missing_cells = int(df[required].isna().sum().sum()) if required else 0
    duplicate_symbols = (
        int(df["Symbol"].astype(str).duplicated().sum()) if "Symbol" in df.columns else 0
    )
    invalid_numeric = 0
    for column in ("Price", "RSI", "AI Score"):
        if column in df.columns:
            values = pd.to_numeric(df[column], errors="coerce")
            invalid_numeric += int((values.isna() | ~values.map(math.isfinite)).sum())

    col1, col2, col3 = st.columns(3)
    col1.metric("Rows returned", len(df))
    col2.metric("Missing required cells", missing_cells)
    col3.metric("Duplicate symbols", duplicate_symbols)
    if invalid_numeric:
        st.warning(
            f"{invalid_numeric} numeric field value(s) are missing or invalid. Review the rows before relying on them."
        )
    elif missing_cells or duplicate_symbols:
        st.warning("Some returned data needs review. Check missing cells and duplicate symbols.")
    else:
        st.success("Returned rows passed the available completeness and numeric checks.")
    st.caption(
        "These checks cover only rows returned by the scanner; they do not verify quote freshness or validate the underlying data provider."
    )


def show():
    st.title("📡 AI Market Scanner")
    st.caption("Professional Scanner")

    settings = st.session_state.get("app_settings", {})
    exchange_preference = settings.get("exchange", "NSE + BSE")
    settings_min_price = float(settings.get("min_price", 0.0) or 0.0)
    min_volume = int(settings.get("min_volume", 0) or 0)
    selected_exchange = (
        exchange_preference if exchange_preference in ("NSE", "BSE") else "NSE + BSE"
    )

    st.caption(
        f"Broad candidate pool: {len(NSE_CANDIDATES)} NSE + {len(BSE_CANDIDATES)} BSE symbols. "
        f"Exchange preference: {selected_exchange}."
    )
    if min_volume > 0:
        st.warning(
            "Minimum volume is saved in Settings but is not applied: current analysis output does not expose traded volume."
        )

    with st.expander("Scanner filters", expanded=True):
        price_col1, price_col2 = st.columns(2)
        with price_col1:
            min_price = st.number_input(
                "Minimum price (₹)",
                min_value=0.0,
                value=settings_min_price,
                step=10.0,
                key="scanner_filter_min_price",
            )
        with price_col2:
            max_price = st.number_input(
                "Maximum price (₹; 0 = no limit)",
                min_value=0.0,
                value=0.0,
                step=10.0,
                key="scanner_filter_max_price",
            )
        rsi_col1, rsi_col2 = st.columns(2)
        with rsi_col1:
            min_rsi = st.number_input(
                "Minimum RSI", min_value=0.0, max_value=100.0, value=0.0, step=1.0
            )
        with rsi_col2:
            max_rsi = st.number_input(
                "Maximum RSI", min_value=0.0, max_value=100.0, value=100.0, step=1.0
            )
        min_ai_score = st.number_input(
            "Minimum AI score", min_value=-100.0, max_value=100.0, value=-100.0, step=1.0
        )
        trend_filter = st.selectbox("Trend", ["All", "Bullish", "Bearish", "Sideways"])

    try:
        _, _, watchlist = get_or_create_default_watchlist(
            None, [f"{symbol}.NS" for symbol in WATCHLIST]
        )
    except WatchlistError as exc:
        # A failed personal-watchlist backend must not crash the broad-market scanner.
        watchlist = [f"{symbol}.NS" for symbol in WATCHLIST]
        st.warning(
            "Personal watchlist storage is unavailable; using the built-in scanner "
            f"watchlist for this session. Details: {exc}"
        )

    if not watchlist:
        st.info("Your Personal Watchlist is empty. Add stocks in the Market page first.")

    scan_mode = st.radio("Scan", ["Personal Watchlist", "Broad Market"], horizontal=True)
    exchange_filter = st.selectbox(
        "Exchange",
        ["NSE + BSE", "NSE", "BSE"],
        help="NSE + BSE keeps opportunities from both exchanges in the candidate pool. "
        "Low-liquidity stocks are not removed; use the Risk and turnover information for judgment.",
    )
    if st.button("Scan", use_container_width=True):
        with st.spinner("Scanning stocks..."):
            df = (
                scan_watchlist(watchlist)
                if scan_mode == "Personal Watchlist"
                else market_scan(exchange_filter)
            )
        scanner_coverage = df.attrs.get("scanner_coverage", {})

        if scan_mode == "Broad Market" and scanner_coverage:
            with st.expander("Scan coverage diagnostics", expanded=True):
                st.caption(
                    "Coverage counts describe the broad-market scan pipeline. "
                    "History rejections include symbols without usable two-candle price/volume history."
                )
                coverage_rows = [
                    {"Exchange": exchange, **counts}
                    for exchange, counts in scanner_coverage.items()
                ]
                st.dataframe(coverage_rows, use_container_width=True, hide_index=True)

        if df.empty:
            st.warning("No stocks could be analyzed for this scan.")
            return

        if exchange_filter in ("NSE", "BSE") and "Exchange" in df.columns:
            df = df.loc[df["Exchange"] == exchange_filter]
        if "Price" in df.columns:
            df = df.loc[df["Price"] >= max(min_price, settings_min_price)]
            if max_price > 0:
                df = df.loc[df["Price"] <= max_price]
        if "RSI" in df.columns:
            df = df.loc[df["RSI"].between(min_rsi, max_rsi)]
        if "AI Score" in df.columns:
            df = df.loc[df["AI Score"] >= min_ai_score]
        if trend_filter != "All" and "Trend" in df.columns:
            df = df.loc[df["Trend"].astype(str).str.casefold() == trend_filter.casefold()]

        if df.empty:
            st.warning(
                "No results match these filters. Widen the price, RSI, score, trend, or exchange settings and scan again."
            )
            return

        _show_data_quality(df)
        st.success(f"{len(df)} matching stocks displayed")
        st.dataframe(
            df.head(DISPLAY_COUNT) if scan_mode == "Broad Market" else df,
            use_container_width=True,
            height=600,
        )
        st.download_button("⬇ Download CSV", df.to_csv(index=False), "market_scan.csv", "text/csv")
