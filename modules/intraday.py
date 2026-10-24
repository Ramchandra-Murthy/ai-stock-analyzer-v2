from __future__ import annotations

from datetime import date, datetime
from time import perf_counter
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import yfinance as yf

from scanner.eros_fusion import compute_eros_fusion
from scanner.eros_fusion_history import append_eros_fusion_snapshot
from scanner.eros_fusion_history_analytics import summarize_eros_fusion_history
from scanner.eros_fusion_trend import analyze_eros_fusion_trend
from scanner.eros_master_dashboard import build_eros_master_dashboard
from scanner.eros_multi_window_trend import analyze_eros_multi_window_trend
from scanner.eros_regime_breadth import analyze_eros_regime_breadth
from scanner.eros_regime_consistency import analyze_eros_regime_consistency
from scanner.eros_regime_dashboard import build_eros_regime_dashboard_snapshot
from scanner.eros_regime_distribution import analyze_eros_regime_distribution
from scanner.eros_regime_duration import analyze_eros_regime_duration
from scanner.eros_regime_history import (
    append_eros_regime_snapshot,
    summarize_eros_regime_history,
)
from scanner.eros_regime_history_comparison import analyze_eros_regime_history_comparison
from scanner.eros_regime_momentum import analyze_eros_regime_momentum
from scanner.eros_regime_persistence import analyze_eros_regime_persistence
from scanner.eros_regime_quality import analyze_eros_regime_quality
from scanner.eros_regime_recency import analyze_eros_regime_recency
from scanner.eros_regime_stability import analyze_eros_regime_stability
from scanner.eros_regime_transition_intervals import analyze_eros_regime_transition_intervals
from scanner.eros_regime_transition_matrix import analyze_eros_regime_transition_matrix
from scanner.eros_regime_transitions import analyze_eros_regime_transitions
from scanner.eros_signal_lifecycle import analyze_eros_signal_lifecycle
from scanner.eros_signal_lifecycle_transitions import analyze_eros_signal_lifecycle_transitions
from scanner.eros_trend_confidence import analyze_eros_trend_confidence
from scanner.eros_trend_consensus import analyze_eros_trend_consensus
from scanner.eros_trend_persistence import analyze_eros_trend_persistence
from scanner.eros_trend_quality import analyze_eros_trend_quality
from scanner.eros_trend_regime import analyze_eros_trend_regime
from scanner.eros_trend_transitions import analyze_eros_trend_transitions
from scanner.institutional_flow import fetch_fii_dii_flow, fetch_fii_dii_history
from scanner.institutional_momentum import compute_institutional_momentum
from scanner.institutional_momentum_history import append_momentum_snapshot
from scanner.intraday_confluence_analytics import summarize_confluence_history
from scanner.intraday_confluence_history import append_confluence_snapshot
from scanner.intraday_signal_confluence import compute_signal_confluence
from scanner.price_jump import scan_price_jumps
from scanner.price_jump_confluence import match_price_jumps_to_confluence
from scanner.price_jump_history import append_price_jump_snapshot
from scanner.price_jump_history_analytics import summarize_price_jump_history
from scanner.unusual_activity import scan_unusual_activity

IST = ZoneInfo("Asia/Kolkata")


def _ticker(symbol: str, exchange: str) -> str:
    cleaned = symbol.strip().upper()
    suffix = ".NS" if exchange == "NSE" else ".BO"
    return cleaned if cleaned.endswith((".NS", ".BO")) else f"{cleaned}{suffix}"


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def _prepare(intraday: pd.DataFrame) -> pd.DataFrame:
    data = intraday.copy()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    required = {"Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(data.columns):
        raise ValueError("The data provider did not return all required OHLCV fields.")
    data = data.dropna(subset=list(required)).sort_index()
    data = data[~data.index.duplicated(keep="last")]
    if data.empty:
        return data
    data["EMA 9"] = data["Close"].ewm(span=9, adjust=False).mean()
    data["EMA 21"] = data["Close"].ewm(span=21, adjust=False).mean()
    data["RSI 14"] = _rsi(data["Close"])
    ema12 = data["Close"].ewm(span=12, adjust=False).mean()
    ema26 = data["Close"].ewm(span=26, adjust=False).mean()
    data["MACD"] = ema12 - ema26
    data["MACD signal"] = data["MACD"].ewm(span=9, adjust=False).mean()
    typical = (data["High"] + data["Low"] + data["Close"]) / 3
    session = pd.Series(data.index.date, index=data.index)
    data["VWAP"] = (typical * data["Volume"]).groupby(session).cumsum() / data["Volume"].groupby(
        session
    ).cumsum().replace(0, float("nan"))
    return data


# NSE/BSE equity-market holidays for 2026 from the official exchange calendar.
# The set prevents a prior-session Yahoo candle from being classified as stale on holidays.
NSE_BSE_EQUITY_HOLIDAYS_2026 = frozenset(
    {
        date(2026, 1, 26),
        date(2026, 3, 3),
        date(2026, 3, 26),
        date(2026, 3, 31),
        date(2026, 4, 3),
        date(2026, 4, 14),
        date(2026, 5, 1),
        date(2026, 5, 28),
        date(2026, 6, 26),
        date(2026, 9, 14),
        date(2026, 10, 2),
        date(2026, 10, 20),
        date(2026, 11, 10),
        date(2026, 11, 24),
        date(2026, 12, 25),
    }
)


def _is_equity_market_holiday(day: date) -> bool:
    return day in NSE_BSE_EQUITY_HOLIDAYS_2026


def _market_session_is_open(now: datetime) -> bool:
    return (
        now.weekday() < 5
        and not _is_equity_market_holiday(now.date())
        and ((now.hour, now.minute) >= (9, 15) and (now.hour, now.minute) < (15, 30))
    )


# Dynamic market board settings.
LIVE_BOARD_REFRESH_SECONDS = 120
LIVE_BOARD_CHUNK_SIZE = 10

# Broad sector labels for the NSE universe. BSE scrips without a verified
# mapping are shown as "Unclassified" rather than inventing a sector.
SECTOR_BY_SYMBOL = {
    "RELIANCE": "Energy",
    "TCS": "IT",
    "INFY": "IT",
    "HCLTECH": "IT",
    "WIPRO": "IT",
    "TECHM": "IT",
    "HDFCBANK": "Financials",
    "ICICIBANK": "Financials",
    "SBIN": "Financials",
    "KOTAKBANK": "Financials",
    "AXISBANK": "Financials",
    "BAJFINANCE": "Financials",
    "BAJAJFINSV": "Financials",
    "INDUSINDBK": "Financials",
    "BANKBARODA": "Financials",
    "CANBK": "Financials",
    "IDFCFIRSTB": "Financials",
    "PNB": "Financials",
    "ICICIGI": "Financials",
    "SBILIFE": "Financials",
    "HDFCLIFE": "Financials",
    "LICI": "Financials",
    "LT": "Industrials",
    "BEL": "Industrials",
    "HAL": "Industrials",
    "SIEMENS": "Industrials",
    "ABB": "Industrials",
    "ADANIENT": "Industrials",
    "ADANIPORTS": "Industrials",
    "IRFC": "Industrials",
    "RVNL": "Industrials",
    "ITC": "Consumer",
    "HINDUNILVR": "Consumer",
    "NESTLEIND": "Consumer",
    "BRITANNIA": "Consumer",
    "TATACONSUM": "Consumer",
    "DABUR": "Consumer",
    "GODREJCP": "Consumer",
    "COLPAL": "Consumer",
    "TITAN": "Consumer",
    "TRENT": "Consumer",
    "DMART": "Consumer",
    "NYKAA": "Consumer",
    "MARUTI": "Automobiles",
    "M&M": "Automobiles",
    "TATAMOTORS": "Automobiles",
    "EICHERMOT": "Automobiles",
    "HEROMOTOCO": "Automobiles",
    "BAJAJ-AUTO": "Automobiles",
    "TVSMOTOR": "Automobiles",
    "ASHOKLEY": "Automobiles",
    "MOTHERSON": "Automobiles",
    "SUNPHARMA": "Pharma",
    "CIPLA": "Pharma",
    "DRREDDY": "Pharma",
    "DIVISLAB": "Pharma",
    "APOLLOHOSP": "Healthcare",
    "ULTRACEMCO": "Cement",
    "GRASIM": "Diversified",
    "HINDALCO": "Metals",
    "TATASTEEL": "Metals",
    "JSWSTEEL": "Metals",
    "VEDL": "Metals",
    "COALINDIA": "Mining",
    "ONGC": "Energy",
    "BPCL": "Energy",
    "IOC": "Energy",
    "GAIL": "Energy",
    "NTPC": "Utilities",
    "POWERGRID": "Utilities",
    "ASIANPAINT": "Materials",
    "PIDILITIND": "Materials",
    "HAVELLS": "Consumer Durables",
    "BHARTIARTL": "Telecom",
    "INDIGO": "Airlines",
    "LODHA": "Real Estate",
    "ZOMATO": "Internet",
    "PAYTM": "Financial Technology",
    "JIOFIN": "Financials",
}


def _live_board_ticker(symbol: str, exchange: str) -> str:
    cleaned = str(symbol).strip().upper()
    suffix = ".NS" if exchange == "NSE" else ".BO"
    return cleaned if cleaned.endswith((".NS", ".BO")) else f"{cleaned}{suffix}"


def _frame_from_board_download(history: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if history is None or history.empty:
        return pd.DataFrame()
    if isinstance(history.columns, pd.MultiIndex):
        if ticker not in history.columns.get_level_values(0):
            return pd.DataFrame()
        frame = history[ticker].copy()
    else:
        frame = history.copy()
    required = {"Close"}
    if not required.issubset(frame.columns):
        return pd.DataFrame()
    frame = frame.dropna(subset=["Close"]).sort_index()
    return frame[~frame.index.duplicated(keep="last")]


@st.cache_data(ttl=LIVE_BOARD_REFRESH_SECONDS, show_spinner=False)
def _fetch_live_board() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, int | float]]:
    """Build a dynamic 20-stock board from the broad NSE+BSE universe."""
    from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES

    candidates = [(symbol, "NSE") for symbol in NSE_CANDIDATES] + [
        (symbol, "BSE") for symbol in BSE_CANDIDATES
    ]
    rows: list[dict[str, object]] = []
    scan_started = perf_counter()
    stats = {
        "candidates": len(candidates),
        "usable": 0,
        "failed_chunks": 0,
        "chunks": 0,
        "download_seconds": 0.0,
        "processing_seconds": 0.0,
        "benchmark_seconds": 0.0,
        "signals_seconds": 0.0,
        "scan_seconds": 0.0,
    }

    for exchange in ("NSE", "BSE"):
        symbols = [symbol for symbol, venue in candidates if venue == exchange]
        tickers = [_live_board_ticker(symbol, exchange) for symbol in symbols]
        for start in range(0, len(tickers), LIVE_BOARD_CHUNK_SIZE):
            chunk = tickers[start : start + LIVE_BOARD_CHUNK_SIZE]
            stats["chunks"] += 1
            download_started = perf_counter()
            try:
                history = yf.download(
                    tickers=chunk,
                    period="5d",
                    interval="1m",
                    progress=False,
                    auto_adjust=False,
                    group_by="ticker",
                    threads=False,
                )
                daily_history = yf.download(
                    tickers=chunk,
                    period="5d",
                    interval="1d",
                    progress=False,
                    auto_adjust=False,
                    group_by="ticker",
                    threads=False,
                )
                stats["download_seconds"] += perf_counter() - download_started
            except Exception:
                stats["download_seconds"] += perf_counter() - download_started
                stats["failed_chunks"] += 1
                continue

            processing_started = perf_counter()
            for ticker in chunk:
                frame = _frame_from_board_download(history, ticker)
                if len(frame) < 2:
                    continue
                stats["usable"] += 1
                close = pd.to_numeric(frame["Close"], errors="coerce").dropna()
                if len(close) < 2:
                    continue
                price = float(close.iloc[-1])
                previous_bar = float(close.iloc[-2])
                change_2m = (price / float(close.iloc[-3]) - 1.0) * 100 if len(close) >= 3 else None
                change_3m = (price / float(close.iloc[-4]) - 1.0) * 100 if len(close) >= 4 else None
                change_5m = (price / float(close.iloc[-6]) - 1.0) * 100 if len(close) >= 6 else None
                change_10m = (
                    (price / float(close.iloc[-11]) - 1.0) * 100 if len(close) >= 11 else None
                )
                change_15m = (
                    (price / float(close.iloc[-16]) - 1.0) * 100 if len(close) >= 16 else None
                )
                volume_surge = None
                if "Volume" in frame.columns:
                    volumes = pd.to_numeric(frame["Volume"], errors="coerce").dropna()
                    if len(volumes) >= 6 and float(volumes.iloc[-1]) > 0:
                        baseline = (
                            float(volumes.iloc[-21:-1].median())
                            if len(volumes) >= 21
                            else float(volumes.iloc[:-1].median())
                        )
                        if baseline > 0:
                            volume_surge = float(volumes.iloc[-1] / baseline)
                breakout = False
                if "High" in frame.columns and len(frame) >= 21:
                    highs = pd.to_numeric(frame["High"], errors="coerce").dropna()
                    if len(highs) >= 21:
                        breakout = price > float(highs.iloc[-21:-1].max())
                if price <= 0 or previous_bar <= 0:
                    continue

                today_change = None
                try:
                    daily_frame = _frame_from_board_download(daily_history, ticker)
                    daily_close = pd.to_numeric(daily_frame["Close"], errors="coerce").dropna()
                    if len(daily_close) >= 2 and float(daily_close.iloc[-2]) > 0:
                        today_change = (price / float(daily_close.iloc[-2]) - 1.0) * 100
                except (KeyError, TypeError, ValueError, IndexError):
                    today_change = None

                symbol = ticker.rsplit(".", 1)[0]
                rows.append(
                    {
                        "Symbol": symbol,
                        "Exchange": exchange,
                        "Sector": SECTOR_BY_SYMBOL.get(symbol, "Unclassified"),
                        "Price": round(price, 2),
                        "1-min change %": round((price / previous_bar - 1.0) * 100, 2),
                        "2-min change %": round(change_2m, 2) if change_2m is not None else None,
                        "3-min change %": round(change_3m, 2) if change_3m is not None else None,
                        "5-min change %": round(change_5m, 2) if change_5m is not None else None,
                        "10-min change %": (
                            round(change_10m, 2) if change_10m is not None else None
                        ),
                        "15-min change %": (
                            round(change_15m, 2) if change_15m is not None else None
                        ),
                        "Volume surge x": (
                            round(volume_surge, 2) if volume_surge is not None else None
                        ),
                        "Breakout": "YES" if breakout else "—",
                        "Today change %": (
                            round(today_change, 2) if today_change is not None else None
                        ),
                        "Last update": str(close.index[-1]),
                    }
                )

    stats["processing_seconds"] += perf_counter() - processing_started

    board = pd.DataFrame(rows)
    if board.empty:
        stats["scan_seconds"] = round(perf_counter() - scan_started, 2)
        return board, pd.DataFrame(), pd.DataFrame(), stats

    nifty_1m = nifty_5m = nifty_today = None
    benchmark_started = perf_counter()
    try:
        benchmark = yf.download(
            "^NSEI",
            period="5d",
            interval="1m",
            progress=False,
            auto_adjust=False,
        )
        benchmark_frame = _frame_from_board_download(benchmark, "^NSEI")
        benchmark_close = pd.to_numeric(benchmark_frame["Close"], errors="coerce").dropna()
        if len(benchmark_close) >= 2:
            nifty_1m = (float(benchmark_close.iloc[-1]) / float(benchmark_close.iloc[-2]) - 1) * 100
        if len(benchmark_close) >= 6:
            nifty_5m = (float(benchmark_close.iloc[-1]) / float(benchmark_close.iloc[-6]) - 1) * 100
        daily_benchmark = yf.download(
            "^NSEI",
            period="5d",
            interval="1d",
            progress=False,
            auto_adjust=False,
        )
        daily_frame = _frame_from_board_download(daily_benchmark, "^NSEI")
        daily_close = pd.to_numeric(daily_frame["Close"], errors="coerce").dropna()
        if len(daily_close) >= 2:
            nifty_today = (float(benchmark_close.iloc[-1]) / float(daily_close.iloc[-2]) - 1) * 100
    except (KeyError, TypeError, ValueError, IndexError):
        pass
    stats["benchmark_seconds"] = perf_counter() - benchmark_started

    board["vs NIFTY 1-min %"] = board["1-min change %"] - nifty_1m if nifty_1m is not None else None
    board["vs NIFTY 5-min %"] = board["5-min change %"] - nifty_5m if nifty_5m is not None else None
    board["vs NIFTY Today %"] = (
        board["Today change %"] - nifty_today if nifty_today is not None else None
    )
    sector_avg = board.groupby("Sector")["Today change %"].transform("mean")
    board["vs Sector Today %"] = board["Today change %"] - sector_avg
    board["Relative Strength"] = (
        board["vs NIFTY Today %"].fillna(0) + board["vs Sector Today %"].fillna(0)
    ) / 2

    sector_summary = (
        board.groupby("Sector", dropna=False)
        .agg(
            Stocks=("Symbol", "count"),
            Advancers=("Today change %", lambda values: int((values > 0).sum())),
            Decliners=("Today change %", lambda values: int((values < 0).sum())),
            Avg_change_pct=("Today change %", "mean"),
            Avg_1min_pct=("1-min change %", "mean"),
        )
        .reset_index()
        .rename(columns={"Avg_change_pct": "Avg change %", "Avg_1min_pct": "Avg 1-min %"})
    )
    sector_summary["Breadth"] = sector_summary["Advancers"] - sector_summary["Decliners"]
    sector_summary = sector_summary.sort_values(
        ["Breadth", "Avg change %", "Stocks"],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    signals_started = perf_counter()
    signals = board[
        (board["2-min change %"].fillna(-999) >= 0.75)
        | (board["3-min change %"].fillna(-999) >= 1.0)
        | (board["Volume surge x"].fillna(0) >= 1.5)
        | (board["Breakout"] == "YES")
    ].copy()
    if not signals.empty:
        signals["Signal"] = "PRICE JUMP"
        signals.loc[signals["Volume surge x"].fillna(0) >= 1.5, "Signal"] = "VOLUME + PRICE"
        signals.loc[signals["Breakout"] == "YES", "Signal"] = "BREAKOUT"
        signals["Momentum score"] = (
            (signals["2-min change %"].fillna(0) / 0.75)
            .clip(lower=0)
            .combine(
                (signals["3-min change %"].fillna(0) / 1.0).clip(lower=0),
                max,
            )
            .combine(
                (signals["5-min change %"].fillna(0) / 1.5).clip(lower=0),
                max,
            )
            .combine(
                (signals["10-min change %"].fillna(0) / 2.0).clip(lower=0),
                max,
            )
            .combine(
                (signals["15-min change %"].fillna(0) / 2.5).clip(lower=0),
                max,
            )
            .combine(
                (signals["Volume surge x"].fillna(0) / 1.5).clip(lower=0),
                max,
            )
        )
        signals.loc[signals["Breakout"] == "YES", "Momentum score"] = signals[
            "Momentum score"
        ].clip(lower=1.0)
        signals = signals.sort_values(
            ["Momentum score", "3-min change %", "2-min change %"],
            ascending=[False, False, False],
            na_position="last",
        ).reset_index(drop=True)

    stats["signals_seconds"] = perf_counter() - signals_started

    board = (
        board.sort_values(
            ["Relative Strength", "1-min change %", "Today change %"],
            ascending=[False, False, False],
            na_position="last",
        )
        .head(20)
        .reset_index(drop=True)
    )
    board.insert(0, "Rank", range(1, len(board) + 1))
    stats["scan_seconds"] = round(perf_counter() - scan_started, 2)
    return board, signals, sector_summary, stats


def _signal_freshness_label(age: float) -> str:
    if pd.isna(age):
        return "UNKNOWN"
    if age <= 3:
        return "FRESH"
    if age <= 5:
        return "AGING"
    return "STALE"


def _show_live_20_panel() -> None:
    st.subheader("📈 Live 20-Stock Market Board")
    st.caption(
        "Top 20 positive movers selected dynamically from the current NSE+BSE candidate universe across sectors. "
        "Prices use Yahoo Finance 1-minute candles and refresh about every 2 minutes; this is not a tick-by-tick exchange feed."
    )

    @st.fragment(run_every=LIVE_BOARD_REFRESH_SECONDS)
    def _live_board_fragment() -> None:
        board, signals, sector_summary, stats = _fetch_live_board()
        if board.empty:
            st.warning(
                "No live board data is currently available. Try again during market hours or check the data provider."
            )
            return

        st.session_state["live_board"] = board.copy()
        st.session_state["live_sector_summary"] = sector_summary.copy()

        now = datetime.now(IST)
        market_open = _market_session_is_open(now)
        latest_candle = pd.to_datetime(board["Last update"], errors="coerce").max()
        freshness_text = (
            f"Latest Yahoo candle: {latest_candle:%d %b %Y, %H:%M:%S %Z}"
            if pd.notna(latest_candle)
            else "Latest Yahoo candle: unavailable"
        )
        market_text = (
            "Market status: OPEN · Yahoo 1-minute data is expected to be current."
            if market_open
            else "Market status: CLOSED · Yahoo may be showing the latest available session candles."
        )
        latest_age_seconds = None
        if pd.notna(latest_candle):
            try:
                latest_ts = pd.Timestamp(latest_candle)
                if latest_ts.tzinfo is None:
                    latest_ts = latest_ts.tz_localize(IST)
                else:
                    latest_ts = latest_ts.tz_convert(IST)
                latest_age_seconds = max(
                    0.0,
                    (pd.Timestamp.now(tz=IST) - latest_ts).total_seconds(),
                )
            except (TypeError, ValueError):
                latest_age_seconds = None

        if stats["failed_chunks"] > 0:
            data_health = "DEGRADED"
        elif latest_age_seconds is None:
            data_health = "UNKNOWN"
        elif market_open and latest_age_seconds > 180:
            data_health = "STALE"
        else:
            data_health = "HEALTHY"

        st.caption(
            f"Checked: {now:%d %b %Y, %H:%M:%S IST} · "
            f"Universe checked: {stats['candidates']} · Usable symbols: {stats['usable']} · "
            f"Refresh: ~{LIVE_BOARD_REFRESH_SECONDS // 60} min"
        )
        status_cols = st.columns(6)
        status_cols[0].metric("Market", "OPEN" if market_open else "CLOSED")
        status_cols[1].metric("Universe", f"{stats['candidates']:,}")
        status_cols[2].metric("Usable", f"{stats['usable']:,}")
        status_cols[3].metric("Signals", f"{len(signals):,}")
        status_cols[4].metric("Scan time", f"{stats['scan_seconds']:.1f}s")
        status_cols[5].metric("Data health", data_health)

        with st.expander("⚙️ Scan diagnostics", expanded=False):
            diagnostic_cols = st.columns(5)
            diagnostic_cols[0].metric("Downloads", f"{stats['download_seconds']:.1f}s")
            diagnostic_cols[1].metric("Processing", f"{stats['processing_seconds']:.1f}s")
            diagnostic_cols[2].metric("Benchmark", f"{stats['benchmark_seconds']:.1f}s")
            diagnostic_cols[3].metric("Signal calc", f"{stats['signals_seconds']:.1f}s")
            diagnostic_cols[4].metric("Chunks", f"{stats['chunks']:,}")
            st.caption(
                f"Failed chunks: {stats['failed_chunks']:,} · "
                "Use these timings to distinguish data-provider/download delays "
                "from local processing time."
            )

        freshness_detail = (
            f" · Data age: {latest_age_seconds:.0f}s" if latest_age_seconds is not None else ""
        )
        st.info(f"{market_text} {freshness_text}{freshness_detail}")
        confluence = compute_signal_confluence(board)
        if not confluence.empty and "Last update" in confluence.columns:
            signal_times = pd.to_datetime(confluence["Last update"], errors="coerce", utc=True)
            signal_age_minutes = (
                (pd.Timestamp.now(tz="UTC") - signal_times).dt.total_seconds().div(60).clip(lower=0)
            )
            confluence["Signal age"] = signal_age_minutes.round(1)
            confluence["Signal freshness"] = confluence["Signal age"].map(_signal_freshness_label)
        st.session_state["live_confluence"] = confluence.copy()
        if not confluence.empty:
            st.subheader("🎯 Intraday Signal Confluence")
            st.caption(
                "Descriptive confluence score across 2m/3m/5m/10m/15m momentum, volume surge, "
                "breakout status, and relative strength. It is a screening metric, not a trade instruction."
            )
            st.dataframe(
                confluence[
                    [
                        "Symbol",
                        "Exchange",
                        "Sector",
                        "Price",
                        "Confluence Score",
                        "Confluence",
                        "Signal age",
                        "Signal freshness",
                        "3-min change %",
                        "5-min change %",
                        "Volume surge x",
                        "Breakout",
                        "Relative Strength",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

            confluence_history = append_confluence_snapshot(
                st.session_state.get("intraday_confluence_history"),
                now,
                confluence,
            )
            st.session_state["intraday_confluence_history"] = confluence_history
            if not confluence_history.empty:
                st.caption("Session history of confluence scores at or above 75.")
                history_display = confluence_history.sort_values(
                    "Timestamp", ascending=False
                ).copy()
                history_display["Timestamp"] = history_display["Timestamp"].dt.strftime(
                    "%d %b %Y, %H:%M:%S"
                )
                st.dataframe(
                    history_display.head(20),
                    use_container_width=True,
                    hide_index=True,
                )
                st.download_button(
                    "Download confluence history CSV",
                    confluence_history.to_csv(index=False).encode("utf-8"),
                    file_name="intraday_confluence_history.csv",
                    mime="text/csv",
                    key="download_intraday_confluence_history",
                )

                confluence_summary = summarize_confluence_history(confluence_history)
                if not confluence_summary.empty:
                    st.subheader("📊 Confluence Persistence Analytics")
                    st.caption(
                        "Session summary of repeated high-confluence observations by symbol."
                    )
                    summary_display = confluence_summary.copy()
                    for column in ["First_Seen", "Last_Seen"]:
                        summary_display[column] = summary_display[column].dt.strftime(
                            "%d %b %Y, %H:%M:%S"
                        )
                    st.dataframe(
                        summary_display.head(20),
                        use_container_width=True,
                        hide_index=True,
                    )
        st.dataframe(
            board,
            use_container_width=True,
            hide_index=True,
            height=620,
            column_config={
                "Price": st.column_config.NumberColumn("Price (₹)", format="₹ %.2f"),
                "1-min change %": st.column_config.NumberColumn("1-min %", format="%.2f%%"),
                "Today change %": st.column_config.NumberColumn("Today %", format="%.2f%%"),
            },
        )

        st.subheader("🏭 Sector Momentum & Market Breadth")
        st.caption(
            "Sector figures use symbols with usable Yahoo Finance data from the current NSE+BSE candidate universe."
        )
        total = int(sector_summary["Stocks"].sum())
        advances = int(sector_summary["Advancers"].sum())
        declines = int(sector_summary["Decliners"].sum())
        unchanged = max(total - advances - declines, 0)
        breadth_ratio = advances / declines if declines else float("inf")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Stocks", total)
        col2.metric("Advancing", advances)
        col3.metric("Declining", declines)
        col4.metric("A/D ratio", "∞" if declines == 0 else f"{breadth_ratio:.2f}")

        st.dataframe(
            sector_summary[
                [
                    "Sector",
                    "Stocks",
                    "Advancers",
                    "Decliners",
                    "Breadth",
                    "Avg change %",
                    "Avg 1-min %",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Avg change %": st.column_config.NumberColumn("Avg today %", format="%.2f%%"),
                "Avg 1-min %": st.column_config.NumberColumn("Avg 1-min %", format="%.2f%%"),
            },
        )
        st.caption(
            f"Universe breadth: {advances} advancing · {declines} declining · {unchanged} unchanged/unknown."
        )

        st.subheader("💪 Relative Strength vs NIFTY & Sector")
        st.caption(
            "Descriptive comparison: stock return minus NIFTY 50 return and minus its current "
            "board-sector average. It is a screening metric, not a trade instruction."
        )
        st.dataframe(
            board[
                [
                    "Symbol",
                    "Exchange",
                    "Sector",
                    "Price",
                    "vs NIFTY 1-min %",
                    "vs NIFTY 5-min %",
                    "vs NIFTY Today %",
                    "vs Sector Today %",
                    "Relative Strength",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Price": st.column_config.NumberColumn("Price (₹)", format="₹ %.2f"),
                "vs NIFTY 1-min %": st.column_config.NumberColumn(
                    "vs NIFTY 1-min", format="%.2f%%"
                ),
                "vs NIFTY 5-min %": st.column_config.NumberColumn(
                    "vs NIFTY 5-min", format="%.2f%%"
                ),
                "vs NIFTY Today %": st.column_config.NumberColumn(
                    "vs NIFTY today", format="%.2f%%"
                ),
                "vs Sector Today %": st.column_config.NumberColumn(
                    "vs sector today", format="%.2f%%"
                ),
                "Relative Strength": st.column_config.NumberColumn(
                    "Relative strength", format="%.2f"
                ),
            },
        )

        st.subheader("⚡ Intraday Price-Jump & Breakout Signals")
        st.caption(
            "Dynamic screen from the same NSE+BSE universe. Signals use 2-minute ≥0.75%, "
            "3-minute ≥1.0%, 5-minute ≥1.5%, 10-minute ≥2.0%, 15-minute ≥2.5%, "
            "volume ≥1.5× recent intraday median, or a prior-20-bar breakout. "
            "Signal status tracks NEW, CONTINUING, WEAKENING, and EXITED across refreshes. "
            "These are screening conditions, not trade instructions."
        )
        if signals.empty:
            st.info(
                "No price-jump, volume-surge, or breakout conditions detected in the current universe."
            )
        else:
            previous_history = st.session_state.get("live_signal_history", {})
            current = set(signals["Symbol"])
            now = datetime.now(IST)
            now_text = now.strftime("%d %b %Y, %H:%M:%S IST")
            active_history = {}
            signal_events = st.session_state.get("live_signal_events", [])
            display = signals.copy()

            for _, row in display.iterrows():
                symbol = row["Symbol"]
                score = float(row["Momentum score"])
                previous = previous_history.get(symbol)
                if previous is None:
                    status = "NEW"
                    first_seen = now_text
                elif score < float(previous.get("score", score)) * 0.90:
                    status = "WEAKENING"
                    first_seen = previous.get("first_seen", now_text)
                else:
                    status = "CONTINUING"
                    first_seen = previous.get("first_seen", now_text)
                active_history[symbol] = {
                    "score": score,
                    "signal": row["Signal"],
                    "first_seen": first_seen,
                    "last_seen": now_text,
                }
                display.loc[display["Symbol"] == symbol, "Status"] = status
                signal_events.append(
                    {
                        "Time": now_text,
                        "Status": status,
                        "Symbol": symbol,
                        "Exchange": row["Exchange"],
                        "Sector": row["Sector"],
                        "Price": float(row["Price"]),
                        "Momentum score": score,
                        "Relative Strength": float(row["Relative Strength"]),
                        "Volume surge x": (
                            float(row["Volume surge x"])
                            if pd.notna(row["Volume surge x"])
                            else None
                        ),
                        "Signal": row["Signal"],
                        "First seen": first_seen,
                    }
                )

            exited = sorted(set(previous_history) - current)
            history_rows = [
                {
                    "Status": "EXITED",
                    "Symbol": symbol,
                    "Signal": previous_history[symbol].get("signal", "—"),
                    "Momentum score": round(float(previous_history[symbol].get("score", 0)), 2),
                    "First seen": previous_history[symbol].get("first_seen", "—"),
                    "Last seen": previous_history[symbol].get("last_seen", "—"),
                }
                for symbol in exited
            ]
            for row in history_rows:
                signal_events.append(
                    {
                        "Time": now_text,
                        "Status": "EXITED",
                        "Symbol": row["Symbol"],
                        "Exchange": "—",
                        "Sector": "—",
                        "Price": None,
                        "Momentum score": row["Momentum score"],
                        "Relative Strength": None,
                        "Volume surge x": None,
                        "Signal": row["Signal"],
                        "First seen": row["First seen"],
                    }
                )

            st.session_state["live_signal_history"] = active_history
            st.session_state["live_signal_events"] = signal_events[-300:]
            display = display.sort_values(
                ["Momentum score", "3-min change %", "2-min change %"],
                ascending=[False, False, False],
                na_position="last",
            ).head(20)
            display.insert(0, "Status", display.pop("Status"))
            st.dataframe(
                display[
                    [
                        "Status",
                        "Symbol",
                        "Exchange",
                        "Sector",
                        "Price",
                        "1-min change %",
                        "2-min change %",
                        "3-min change %",
                        "5-min change %",
                        "10-min change %",
                        "15-min change %",
                        "Today change %",
                        "Volume surge x",
                        "Breakout",
                        "Signal",
                        "Last update",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Price": st.column_config.NumberColumn("Price (₹)", format="₹ %.2f"),
                    "1-min change %": st.column_config.NumberColumn("1-min %", format="%.2f%%"),
                    "2-min change %": st.column_config.NumberColumn("2-min %", format="%.2f%%"),
                    "3-min change %": st.column_config.NumberColumn("3-min %", format="%.2f%%"),
                    "5-min change %": st.column_config.NumberColumn("5-min %", format="%.2f%%"),
                    "10-min change %": st.column_config.NumberColumn("10-min %", format="%.2f%%"),
                    "15-min change %": st.column_config.NumberColumn("15-min %", format="%.2f%%"),
                    "Today change %": st.column_config.NumberColumn("Today %", format="%.2f%%"),
                    "Volume surge x": st.column_config.NumberColumn("Volume x", format="%.2fx"),
                },
            )

            if history_rows:
                st.caption(
                    "Signals that disappeared since the previous refresh are retained below as EXITED."
                )
                st.dataframe(
                    pd.DataFrame(history_rows),
                    use_container_width=True,
                    hide_index=True,
                )

            events = pd.DataFrame(st.session_state.get("live_signal_events", []))
            if not events.empty:
                st.subheader("📊 Intraday Signal History & Analytics")
                st.caption(
                    "Session history records each refresh while the app is running. "
                    "It resets when the Streamlit session ends."
                )
                active_events = events[events["Status"] != "EXITED"]
                frequent = (
                    active_events["Symbol"]
                    .value_counts()
                    .rename_axis("Symbol")
                    .reset_index(name="Refreshes seen")
                    .head(10)
                )
                counts = (
                    events.groupby("Status")["Symbol"].count().rename("Observations").reset_index()
                )
                h1, h2 = st.columns(2)
                with h1:
                    st.caption("Most frequently observed signals")
                    st.dataframe(frequent, use_container_width=True, hide_index=True)
                with h2:
                    st.caption("Signal status observations")
                    st.dataframe(counts, use_container_width=True, hide_index=True)
                st.dataframe(
                    events.sort_values("Time", ascending=False).head(100),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Price": st.column_config.NumberColumn("Price (₹)", format="₹ %.2f"),
                        "Momentum score": st.column_config.NumberColumn("Momentum", format="%.2f"),
                        "Relative Strength": st.column_config.NumberColumn(
                            "Relative strength", format="%.2f"
                        ),
                        "Volume surge x": st.column_config.NumberColumn("Volume x", format="%.2fx"),
                    },
                )
                st.download_button(
                    "Download signal history CSV",
                    events.to_csv(index=False).encode("utf-8"),
                    file_name="intraday_signal_history.csv",
                    mime="text/csv",
                    key="download_signal_history",
                )

    _live_board_fragment()


def show() -> None:
    st.title("⏱️ Intraday Trading")
    st.caption("Technical analysis and paper-trading review — no orders are placed.")

    _show_live_20_panel()
    st.divider()

    st.subheader("Price jump scanner")
    st.caption(
        "Screens candidate stocks for price rises over the selected lookback. The 2- and 3-minute choices use Yahoo Finance 1-minute candles; longer lookbacks use 5-minute candles. This is a retrospective candle screen, not a live tick alert; Yahoo coverage and delays vary."
    )
    jump_exchange = st.selectbox(
        "Exchange for price jumps",
        ["Both", "NSE", "BSE"],
        key="jump_exchange",
        format_func=lambda value: "NSE + BSE" if value == "Both" else value,
    )
    jump_cap = st.selectbox(
        "Market-cap basket for price jumps",
        ["All caps", "Large cap", "Mid cap", "Small cap"],
        key="jump_cap",
    )
    jump_window = st.selectbox(
        "Jump lookback",
        [2, 3, 5, 10, 15, 30],
        index=2,
        format_func=lambda value: f"{value} minutes",
        key="jump_window",
    )
    jump_threshold = st.selectbox(
        "Minimum price rise",
        [0.5, 1.0, 1.5, 2.0, 3.0],
        index=1,
        format_func=lambda value: f"{value:.1f}%",
        key="jump_threshold",
    )
    jump_limit = st.selectbox(
        "Maximum price-jump results", [10, 20, 30, 50], index=1, key="jump_limit"
    )
    if st.button("Scan for price jumps", key="run_price_jump"):
        with st.spinner(f"Checking {jump_exchange} · {jump_cap.lower()} candidates…"):
            try:
                result = scan_price_jumps(
                    jump_limit, jump_cap, jump_exchange, jump_window, jump_threshold
                )
                st.session_state["price_jump_results"] = result
                st.session_state["price_jump_scan_time"] = datetime.now(IST).strftime(
                    "%d %b %Y, %H:%M IST"
                )
                st.session_state["price_jump_scan_exchange"] = jump_exchange
                st.session_state["price_jump_scan_cap"] = jump_cap
                st.session_state["price_jump_scan_window"] = jump_window
                st.session_state["price_jump_history"] = append_price_jump_snapshot(
                    st.session_state.get("price_jump_history"),
                    datetime.now(IST),
                    result,
                )
            except Exception as exc:
                st.error(f"Price-jump scan could not complete: {exc}")
    jump_results = st.session_state.get("price_jump_results")
    if jump_results is not None:
        st.caption(
            f"Last scan: {st.session_state.get('price_jump_scan_time', 'unknown')} · Exchange: {st.session_state.get('price_jump_scan_exchange', 'unknown')} · Basket: {st.session_state.get('price_jump_scan_cap', 'unknown')} · Lookback: {st.session_state.get('price_jump_scan_window', 'unknown')} min · Candidate list is limited, not exchange-wide."
        )
        if jump_results.empty:
            st.info(
                "No candidates met this threshold, or the provider returned insufficient candles. Try a lower threshold or scan during market hours."
            )
        else:
            st.dataframe(jump_results, use_container_width=True, hide_index=True)
            st.download_button(
                "Download price-jump CSV",
                jump_results.to_csv(index=False).encode("utf-8"),
                file_name="price_jumps.csv",
                mime="text/csv",
                key="download_price_jumps",
            )

            live_board = st.session_state.get("live_board")
            if live_board is not None and not live_board.empty:
                confirmed_jumps = match_price_jumps_to_confluence(jump_results, live_board)
                if not confirmed_jumps.empty:
                    st.subheader("🎯 Price Jump + Confluence")
                    st.caption(
                        "Matches price-jump results with the latest live-board confluence metrics. "
                        "Confirmation means confluence score meets the configured 75-point screening threshold; it is not a trade instruction."
                    )
                    st.dataframe(confirmed_jumps, use_container_width=True, hide_index=True)
                    st.download_button(
                        "Download price-jump confluence CSV",
                        confirmed_jumps.to_csv(index=False).encode("utf-8"),
                        file_name="price_jump_confluence.csv",
                        mime="text/csv",
                        key="download_price_jump_confluence",
                    )

    price_jump_history = st.session_state.get("price_jump_history")
    if price_jump_history is not None and not price_jump_history.empty:
        st.subheader("📈 Price-Jump Session History")
        st.caption(
            "Session-scoped record of qualifying price-jump observations. "
            "Repeated observations of the same symbol are retained at different scan times; "
            "duplicate rows from the same scan timestamp are suppressed."
        )
        history_display = price_jump_history.sort_values("Timestamp", ascending=False).copy()
        history_display["Timestamp"] = pd.to_datetime(
            history_display["Timestamp"], errors="coerce"
        ).dt.strftime("%d %b %Y, %H:%M:%S")
        st.dataframe(history_display.head(50), use_container_width=True, hide_index=True)
        st.download_button(
            "Download price-jump history CSV",
            price_jump_history.to_csv(index=False).encode("utf-8"),
            file_name="price_jump_history.csv",
            mime="text/csv",
            key="download_price_jump_history",
        )

        price_jump_summary = summarize_price_jump_history(price_jump_history)
        if not price_jump_summary.empty:
            st.subheader("🔎 Price-Jump Persistence Analytics")
            st.caption(
                "Groups session observations by symbol and exchange to show repeated price-jump activity."
            )
            st.dataframe(
                price_jump_summary.head(30),
                use_container_width=True,
                hide_index=True,
            )

    fusion = compute_eros_fusion(
        st.session_state.get("live_confluence"),
        st.session_state.get("intraday_confluence_history"),
        st.session_state.get("price_jump_results"),
        st.session_state.get("institutional_momentum_score"),
        st.session_state.get("price_jump_history"),
    )
    if not fusion.empty:
        st.subheader("🧩 EROS Signal Fusion")
        st.caption(
            "Transparent screening score combining confluence (50%), confluence persistence (20%), "
            "price-jump persistence (15%), and institutional momentum context (15%). "
            "It is a descriptive screening metric, not a trade instruction."
        )
        st.dataframe(fusion.head(20), use_container_width=True, hide_index=True)
        st.download_button(
            "Download EROS fusion CSV",
            fusion.to_csv(index=False).encode("utf-8"),
            file_name="eros_fusion.csv",
            mime="text/csv",
            key="download_eros_fusion",
        )

        fusion_history = append_eros_fusion_snapshot(
            st.session_state.get("eros_fusion_history"),
            datetime.now(IST),
            fusion,
        )
        st.session_state["eros_fusion_history"] = fusion_history
        if not fusion_history.empty:
            st.subheader("📊 EROS Fusion History")
            st.caption(
                "Session-scoped history of EROS fusion scores across dashboard refreshes. "
                "Repeated observations help distinguish one-time scores from persistent signals."
            )
            history_display = fusion_history.sort_values("Timestamp", ascending=False).copy()
            history_display["Timestamp"] = pd.to_datetime(
                history_display["Timestamp"], errors="coerce"
            ).dt.strftime("%d %b %Y, %H:%M:%S")
            st.dataframe(
                history_display.head(50),
                use_container_width=True,
                hide_index=True,
            )
            st.download_button(
                "Download EROS fusion history CSV",
                fusion_history.to_csv(index=False).encode("utf-8"),
                file_name="eros_fusion_history.csv",
                mime="text/csv",
                key="download_eros_fusion_history",
            )

            fusion_summary = summarize_eros_fusion_history(fusion_history)
            if not fusion_summary.empty:
                st.caption("Persistence summary of repeated EROS fusion observations by symbol.")
                st.dataframe(
                    fusion_summary.head(30),
                    use_container_width=True,
                    hide_index=True,
                )

            fusion_trend = analyze_eros_fusion_trend(fusion_history)
            if not fusion_trend.empty:
                st.subheader("📈 EROS Fusion Trend & Acceleration")
                st.caption(
                    "Compares the latest fusion observation with the previous observation for each symbol. "
                    "Acceleration is the change in the fusion change between observations; this is descriptive analytics, not a trade instruction."
                )
                st.dataframe(
                    fusion_trend.head(30),
                    use_container_width=True,
                    hide_index=True,
                )
                st.download_button(
                    "Download EROS fusion trend CSV",
                    fusion_trend.to_csv(index=False).encode("utf-8"),
                    file_name="eros_fusion_trend.csv",
                    mime="text/csv",
                    key="download_eros_fusion_trend",
                )

                lifecycle = analyze_eros_signal_lifecycle(
                    fusion_history,
                    fusion,
                )
                if not lifecycle.empty:
                    st.subheader("🔄 EROS Signal Lifecycle & Confirmation Matrix")
                    st.caption(
                        "Descriptive lifecycle state derived from repeated EROS observations, "
                        "fusion change, acceleration, and whether the signal is present in the latest "
                        "fusion snapshot. It is an analytics layer, not a trade instruction."
                    )
                    matrix = fusion.merge(
                        lifecycle[
                            [
                                "Symbol",
                                "Exchange",
                                "Observations",
                                "Fusion Change",
                                "Fusion Acceleration",
                                "Trend",
                                "Lifecycle",
                            ]
                        ],
                        on=["Symbol", "Exchange"],
                        how="left",
                    )
                    matrix_columns = [
                        "Symbol",
                        "Exchange",
                        "Sector",
                        "Fusion Score",
                        "Confluence Component",
                        "Persistence Component",
                        "Price Jump Component",
                        "Institutional Component",
                        "Observations",
                        "Fusion Change",
                        "Fusion Acceleration",
                        "Trend",
                        "Lifecycle",
                    ]
                    matrix = matrix[
                        [column for column in matrix_columns if column in matrix.columns]
                    ]
                    st.dataframe(
                        matrix.head(30),
                        use_container_width=True,
                        hide_index=True,
                    )
                    st.download_button(
                        "Download EROS lifecycle matrix CSV",
                        matrix.to_csv(index=False).encode("utf-8"),
                        file_name="eros_signal_lifecycle.csv",
                        mime="text/csv",
                        key="download_eros_signal_lifecycle",
                    )

                    multi_window = analyze_eros_multi_window_trend(fusion_history)
                    if not multi_window.empty:
                        st.subheader("🕒 EROS Multi-Window Trend")
                        st.caption(
                            "Compares fusion-score change over the latest 2, 3, and 5 observations. "
                            "These are observation windows, not separate market-data timeframes."
                        )
                        st.dataframe(
                            multi_window.head(30),
                            use_container_width=True,
                            hide_index=True,
                        )
                        st.download_button(
                            "Download EROS multi-window CSV",
                            multi_window.to_csv(index=False).encode("utf-8"),
                            file_name="eros_multi_window_trend.csv",
                            mime="text/csv",
                            key="download_eros_multi_window_trend",
                        )

                        consensus = analyze_eros_trend_consensus(
                            fusion_history,
                            fusion,
                        )
                        if not consensus.empty:
                            st.subheader("🧭 EROS Trend Consensus")
                            st.caption(
                                "Cross-checks multi-window alignment with latest fusion change, "
                                "acceleration, and lifecycle state. This is descriptive analytics, "
                                "not a trade instruction."
                            )
                            st.dataframe(
                                consensus.head(30),
                                use_container_width=True,
                                hide_index=True,
                            )
                            st.download_button(
                                "Download EROS trend consensus CSV",
                                consensus.to_csv(index=False).encode("utf-8"),
                                file_name="eros_trend_consensus.csv",
                                mime="text/csv",
                                key="download_eros_trend_consensus",
                            )

                            lifecycle_transitions = analyze_eros_signal_lifecycle_transitions(
                                fusion_history
                            )
                            if not lifecycle_transitions.empty:
                                st.subheader("🔄 EROS Signal Lifecycle Transitions")
                                st.caption(
                                    "Tracks the latest lifecycle state, previous state, transition count, "
                                    "and lifecycle age for each signal. This is descriptive analytics, "
                                    "not a trade instruction."
                                )
                                st.dataframe(
                                    lifecycle_transitions.head(30),
                                    use_container_width=True,
                                    hide_index=True,
                                )
                                st.download_button(
                                    "Download EROS lifecycle transitions CSV",
                                    lifecycle_transitions.to_csv(index=False).encode("utf-8"),
                                    file_name="eros_signal_lifecycle_transitions.csv",
                                    mime="text/csv",
                                    key="download_eros_lifecycle_transitions",
                                )

                            transitions = analyze_eros_trend_transitions(fusion_history)
                            if not transitions.empty:
                                st.subheader("🔄 EROS Trend Transitions")
                                st.caption(
                                    "Detects whether the latest fusion-score direction is continuing "
                                    "or has reversed versus the previous observation. This is "
                                    "descriptive analytics, not a trade instruction."
                                )
                                st.dataframe(
                                    transitions.head(30),
                                    use_container_width=True,
                                    hide_index=True,
                                )
                                st.download_button(
                                    "Download EROS trend transitions CSV",
                                    transitions.to_csv(index=False).encode("utf-8"),
                                    file_name="eros_trend_transitions.csv",
                                    mime="text/csv",
                                    key="download_eros_trend_transitions",
                                )

                            persistence = analyze_eros_trend_persistence(fusion_history)
                            if not persistence.empty:
                                st.subheader("📈 EROS Trend Persistence")
                                st.caption(
                                    "Measures the latest directional streak and recent directional "
                                    "consistency of each EROS fusion signal. This is descriptive "
                                    "analytics, not a trade instruction."
                                )
                                st.dataframe(
                                    persistence.head(30),
                                    use_container_width=True,
                                    hide_index=True,
                                )
                                st.download_button(
                                    "Download EROS trend persistence CSV",
                                    persistence.to_csv(index=False).encode("utf-8"),
                                    file_name="eros_trend_persistence.csv",
                                    mime="text/csv",
                                    key="download_eros_trend_persistence",
                                )

                            quality = analyze_eros_trend_quality(fusion_history)
                            if not quality.empty:
                                st.subheader("🧭 EROS Trend Quality")
                                st.caption(
                                    "Measures directional consistency and movement efficiency across the "
                                    "latest EROS fusion observations. This is descriptive analytics, not "
                                    "a trade instruction."
                                )
                                st.dataframe(
                                    quality.head(30),
                                    use_container_width=True,
                                    hide_index=True,
                                )
                                st.download_button(
                                    "Download EROS trend quality CSV",
                                    quality.to_csv(index=False).encode("utf-8"),
                                    file_name="eros_trend_quality.csv",
                                    mime="text/csv",
                                    key="download_eros_trend_quality",
                                )

                            confidence = analyze_eros_trend_confidence(fusion_history)
                            if not confidence.empty:
                                st.subheader("🎯 EROS Trend Confidence")
                                st.caption(
                                    "Combines trend consensus, persistence, and movement efficiency into a "
                                    "transparent descriptive confidence metric. It does not change EROS "
                                    "scoring weights or provide a trade instruction."
                                )
                                st.dataframe(
                                    confidence.head(30),
                                    use_container_width=True,
                                    hide_index=True,
                                )
                                st.download_button(
                                    "Download EROS trend confidence CSV",
                                    confidence.to_csv(index=False).encode("utf-8"),
                                    file_name="eros_trend_confidence.csv",
                                    mime="text/csv",
                                    key="download_eros_trend_confidence",
                                )

                            regime = analyze_eros_trend_regime(confidence)
                            if not regime.empty:
                                st.subheader("🌐 EROS Trend Breadth & Regime")
                                st.caption(
                                    "Aggregates the latest EROS trend-confidence distribution across the "
                                    "scanned universe. Breadth describes the balance of confirmed rising "
                                    "versus falling signals; it is descriptive analytics, not a trade instruction."
                                )
                                st.dataframe(
                                    regime,
                                    use_container_width=True,
                                    hide_index=True,
                                )
                                st.download_button(
                                    "Download EROS trend regime CSV",
                                    regime.to_csv(index=False).encode("utf-8"),
                                    file_name="eros_trend_regime.csv",
                                    mime="text/csv",
                                    key="download_eros_trend_regime",
                                )

                                regime_history = append_eros_regime_snapshot(
                                    st.session_state.get("eros_regime_history"),
                                    datetime.now(IST),
                                    regime,
                                )
                                st.session_state["eros_regime_history"] = regime_history
                                regime_summary = summarize_eros_regime_history(regime_history)
                                if not regime_summary.empty:
                                    st.subheader("🕒 EROS Regime History & Transition")
                                    st.caption(
                                        "Tracks the session history of the aggregate EROS regime and "
                                        "breadth changes. A transition describes a change between successive "
                                        "dashboard snapshots; it is descriptive analytics, not a trade instruction."
                                    )
                                    st.dataframe(
                                        regime_summary,
                                        use_container_width=True,
                                        hide_index=True,
                                    )
                                    history_display = regime_history.sort_values(
                                        "Timestamp", ascending=False
                                    ).copy()
                                    history_display["Timestamp"] = pd.to_datetime(
                                        history_display["Timestamp"], errors="coerce"
                                    ).dt.strftime("%d %b %Y, %H:%M:%S")
                                    st.dataframe(
                                        history_display.head(30),
                                        use_container_width=True,
                                        hide_index=True,
                                    )
                                    st.download_button(
                                        "Download EROS regime history CSV",
                                        regime_history.to_csv(index=False).encode("utf-8"),
                                        file_name="eros_regime_history.csv",
                                        mime="text/csv",
                                        key="download_eros_regime_history",
                                    )

                                    regime_transitions = analyze_eros_regime_transitions(
                                        regime_history
                                    )
                                    if not regime_transitions.empty:
                                        st.subheader("🔄 EROS Regime Transition History")
                                        st.caption(
                                            "Records each aggregate regime change with its timestamp, "
                                            "direction change, and transition type. This is descriptive "
                                            "analytics, not a trade instruction."
                                        )
                                        transition_display = regime_transitions.sort_values(
                                            "Timestamp", ascending=False
                                        ).copy()
                                        transition_display["Timestamp"] = pd.to_datetime(
                                            transition_display["Timestamp"], errors="coerce"
                                        ).dt.strftime("%d %b %Y, %H:%M:%S")
                                        st.dataframe(
                                            transition_display,
                                            use_container_width=True,
                                            hide_index=True,
                                        )
                                        st.download_button(
                                            "Download EROS regime transitions CSV",
                                            regime_transitions.to_csv(index=False).encode("utf-8"),
                                            file_name="eros_regime_transitions.csv",
                                            mime="text/csv",
                                            key="download_eros_regime_transitions",
                                        )

                                    regime_duration = analyze_eros_regime_duration(regime_history)
                                    if not regime_duration.empty:
                                        st.subheader("⏱️ EROS Regime Duration History")
                                        st.caption(
                                            "Measures how long each contiguous aggregate EROS regime "
                                            "remained active in the recorded session snapshots. This is "
                                            "descriptive analytics, not a trade instruction."
                                        )
                                        duration_display = regime_duration.sort_values(
                                            "Run Number", ascending=False
                                        ).copy()
                                        for column in ["Start", "End"]:
                                            duration_display[column] = pd.to_datetime(
                                                duration_display[column], errors="coerce"
                                            ).dt.strftime("%d %b %Y, %H:%M:%S")
                                        st.dataframe(
                                            duration_display,
                                            use_container_width=True,
                                            hide_index=True,
                                        )
                                        st.download_button(
                                            "Download EROS regime duration CSV",
                                            regime_duration.to_csv(index=False).encode("utf-8"),
                                            file_name="eros_regime_duration.csv",
                                            mime="text/csv",
                                            key="download_eros_regime_duration",
                                        )

                                    regime_breadth = analyze_eros_regime_breadth(regime_history)
                                    if not regime_breadth.empty:
                                        st.subheader("📊 EROS Regime Breadth & Strength")
                                        st.caption(
                                            "Summarizes rising/falling breadth and trend confidence "
                                            "within each recorded aggregate regime. This is descriptive "
                                            "analytics, not a trade instruction."
                                        )
                                        st.dataframe(
                                            regime_breadth,
                                            use_container_width=True,
                                            hide_index=True,
                                        )
                                        st.download_button(
                                            "Download EROS regime breadth CSV",
                                            regime_breadth.to_csv(index=False).encode("utf-8"),
                                            file_name="eros_regime_breadth.csv",
                                            mime="text/csv",
                                            key="download_eros_regime_breadth",
                                        )

                                    regime_consistency = analyze_eros_regime_consistency(
                                        regime_history
                                    )
                                    if not regime_consistency.empty:
                                        st.subheader("🔎 EROS Regime Consistency")
                                        st.caption(
                                            "Compares each recorded aggregate regime with the regime "
                                            "implied by its recorded directional breadth. This is "
                                            "descriptive analytics, not a trade instruction."
                                        )
                                        st.dataframe(
                                            regime_consistency,
                                            use_container_width=True,
                                            hide_index=True,
                                        )
                                        st.download_button(
                                            "Download EROS regime consistency CSV",
                                            regime_consistency.to_csv(index=False).encode("utf-8"),
                                            file_name="eros_regime_consistency.csv",
                                            mime="text/csv",
                                            key="download_eros_regime_consistency",
                                        )

                                    regime_quality = analyze_eros_regime_quality(regime_history)
                                    if not regime_quality.empty:
                                        st.subheader("🧭 EROS Regime Quality Dimensions")
                                        st.caption(
                                            "Reports current breadth strength, trend confidence, and "
                                            "historical ranges for the current regime. These are "
                                            "separate descriptive dimensions, not a composite score "
                                            "or trade instruction."
                                        )
                                        st.dataframe(
                                            regime_quality,
                                            use_container_width=True,
                                            hide_index=True,
                                        )
                                        st.download_button(
                                            "Download EROS regime quality CSV",
                                            regime_quality.to_csv(index=False).encode("utf-8"),
                                            file_name="eros_regime_quality.csv",
                                            mime="text/csv",
                                            key="download_eros_regime_quality",
                                        )

                                    regime_persistence = analyze_eros_regime_persistence(
                                        regime_history
                                    )
                                    if not regime_persistence.empty:
                                        st.subheader("📈 EROS Regime Persistence")
                                        st.caption(
                                            "Summarizes how consistently each aggregate EROS regime "
                                            "persists across consecutive snapshots. This is descriptive "
                                            "analytics, not a trade instruction."
                                        )
                                        st.dataframe(
                                            regime_persistence,
                                            use_container_width=True,
                                            hide_index=True,
                                        )
                                        st.download_button(
                                            "Download EROS regime persistence CSV",
                                            regime_persistence.to_csv(index=False).encode("utf-8"),
                                            file_name="eros_regime_persistence.csv",
                                            mime="text/csv",
                                            key="download_eros_regime_persistence",
                                        )

                                    regime_momentum = analyze_eros_regime_momentum(regime_history)
                                    if not regime_momentum.empty:
                                        st.subheader("📈 EROS Regime Momentum")
                                        st.caption(
                                            "Measures recent changes in aggregate breadth and confidence "
                                            "to describe whether the current regime is strengthening, "
                                            "weakening, or stable. It is descriptive analytics, not a trade instruction."
                                        )
                                        st.dataframe(
                                            regime_momentum,
                                            use_container_width=True,
                                            hide_index=True,
                                        )
                                        st.download_button(
                                            "Download EROS regime momentum CSV",
                                            regime_momentum.to_csv(index=False).encode("utf-8"),
                                            file_name="eros_regime_momentum.csv",
                                            mime="text/csv",
                                            key="download_eros_regime_momentum",
                                        )

                                        regime_stability = analyze_eros_regime_stability(
                                            regime_history
                                        )
                                        if not regime_stability.empty:
                                            st.subheader("🧭 EROS Regime Stability")
                                            st.caption(
                                                "Measures the persistence and variability of the current "
                                                "aggregate regime across session snapshots. This is descriptive "
                                                "analytics, not a trade instruction."
                                            )
                                            st.dataframe(
                                                regime_stability,
                                                use_container_width=True,
                                                hide_index=True,
                                            )
                                            st.download_button(
                                                "Download EROS regime stability CSV",
                                                regime_stability.to_csv(index=False).encode(
                                                    "utf-8"
                                                ),
                                                file_name="eros_regime_stability.csv",
                                                mime="text/csv",
                                                key="download_eros_regime_stability",
                                            )

                                        regime_history_comparison = (
                                            analyze_eros_regime_history_comparison(regime_history)
                                        )
                                        if not regime_history_comparison.empty:
                                            st.subheader("🕰️ EROS Historical Comparison")
                                            st.caption(
                                                "Compares the latest regime snapshot with prior session "
                                                "history and prior observations of the same regime. "
                                                "Descriptive analytics only."
                                            )
                                            st.dataframe(
                                                regime_history_comparison,
                                                use_container_width=True,
                                                hide_index=True,
                                            )
                                            st.download_button(
                                                "Download EROS historical comparison CSV",
                                                regime_history_comparison.to_csv(
                                                    index=False
                                                ).encode("utf-8"),
                                                file_name="eros_regime_historical_comparison.csv",
                                                mime="text/csv",
                                                key="download_eros_regime_historical_comparison",
                                            )

                                        regime_distribution = analyze_eros_regime_distribution(
                                            regime_history
                                        )
                                        if not regime_distribution.empty:
                                            st.subheader("📊 EROS Regime Distribution")
                                            st.caption(
                                                "Summarizes how often each observed EROS regime appears in "
                                                "the stored history, with descriptive breadth and trend-confidence "
                                                "statistics. Descriptive analytics only."
                                            )
                                            st.dataframe(
                                                regime_distribution,
                                                use_container_width=True,
                                                hide_index=True,
                                            )
                                            st.download_button(
                                                "Download EROS regime distribution CSV",
                                                regime_distribution.to_csv(index=False).encode(
                                                    "utf-8"
                                                ),
                                                file_name="eros_regime_distribution.csv",
                                                mime="text/csv",
                                                key="download_eros_regime_distribution",
                                            )

                                        regime_recency = analyze_eros_regime_recency(regime_history)
                                        if not regime_recency.empty:
                                            st.subheader("⏱️ EROS Regime Recency")
                                            st.caption(
                                                "Shows how recently the current regime began and "
                                                "its contiguous run duration. Descriptive analytics only."
                                            )
                                            st.dataframe(
                                                regime_recency,
                                                use_container_width=True,
                                                hide_index=True,
                                            )
                                            st.download_button(
                                                "Download EROS regime recency CSV",
                                                regime_recency.to_csv(index=False).encode("utf-8"),
                                                file_name="eros_regime_recency.csv",
                                                mime="text/csv",
                                                key="download_eros_regime_recency",
                                            )

                                        regime_transition_matrix = (
                                            analyze_eros_regime_transition_matrix(regime_history)
                                        )
                                        if not regime_transition_matrix.empty:
                                            st.subheader("🔄 EROS Regime Transition Matrix")
                                            st.caption(
                                                "Summarizes observed changes from one EROS regime to another "
                                                "and their share of recorded transitions. Descriptive analytics only."
                                            )
                                            st.dataframe(
                                                regime_transition_matrix,
                                                use_container_width=True,
                                                hide_index=True,
                                            )
                                            st.download_button(
                                                "Download EROS regime transition matrix CSV",
                                                regime_transition_matrix.to_csv(index=False).encode(
                                                    "utf-8"
                                                ),
                                                file_name="eros_regime_transition_matrix.csv",
                                                mime="text/csv",
                                                key="download_eros_regime_transition_matrix",
                                            )

                                        regime_transition_intervals = (
                                            analyze_eros_regime_transition_intervals(regime_history)
                                        )
                                        if not regime_transition_intervals.empty:
                                            st.subheader("⏱️ EROS Regime Transition Intervals")
                                            st.caption(
                                                "Shows elapsed time between observed EROS regime transitions. "
                                                "The first recorded transition has no prior transition interval. "
                                                "Descriptive analytics only."
                                            )
                                            st.dataframe(
                                                regime_transition_intervals,
                                                use_container_width=True,
                                                hide_index=True,
                                            )
                                            st.download_button(
                                                "Download EROS regime transition intervals CSV",
                                                regime_transition_intervals.to_csv(
                                                    index=False
                                                ).encode("utf-8"),
                                                file_name="eros_regime_transition_intervals.csv",
                                                mime="text/csv",
                                                key="download_eros_regime_transition_intervals",
                                            )

                                        master_summary, master_signals = (
                                            build_eros_master_dashboard(
                                                fusion_history,
                                                fusion,
                                                regime_history,
                                            )
                                        )
                                        regime_dashboard_snapshot = (
                                            build_eros_regime_dashboard_snapshot(regime_history)
                                        )
                                        if not regime_dashboard_snapshot.empty:
                                            st.subheader("🧭 EROS Regime Dashboard Snapshot")
                                            st.caption(
                                                "Consolidates the existing regime dimensions into one "
                                                "current-state view. No new score or trade instruction is "
                                                "created."
                                            )
                                            st.dataframe(
                                                regime_dashboard_snapshot,
                                                use_container_width=True,
                                                hide_index=True,
                                            )
                                            st.download_button(
                                                "Download EROS regime snapshot CSV",
                                                regime_dashboard_snapshot.to_csv(
                                                    index=False
                                                ).encode("utf-8"),
                                                file_name="eros_regime_dashboard_snapshot.csv",
                                                mime="text/csv",
                                                key="download_eros_regime_dashboard_snapshot",
                                            )

                                        if not master_summary.empty:
                                            st.subheader("🧩 EROS Master Dashboard")
                                            st.caption(
                                                "Compact view combining the existing EROS signal lifecycle, "
                                                "trend confidence, fusion score, regime momentum, and regime "
                                                "stability analytics. It is descriptive analytics, not a trade instruction."
                                            )
                                            st.dataframe(
                                                master_summary,
                                                use_container_width=True,
                                                hide_index=True,
                                            )
                                            if not master_signals.empty:
                                                st.dataframe(
                                                    master_signals.head(30),
                                                    use_container_width=True,
                                                    hide_index=True,
                                                )
                                            st.download_button(
                                                "Download EROS master dashboard CSV",
                                                master_signals.to_csv(index=False).encode("utf-8"),
                                                file_name="eros_master_dashboard.csv",
                                                mime="text/csv",
                                                key="download_eros_master_dashboard",
                                            )

    st.subheader("🏦 Institutional Momentum Score")
    st.caption(
        "Composite descriptive score from institutional flow, flow trend, market breadth, sector momentum, "
        "market momentum, and relative strength. It is a screening metric, not a trade instruction."
    )
    score_result = compute_institutional_momentum(
        flow=st.session_state.get("institutional_flow"),
        history=st.session_state.get("institutional_flow_history"),
        board=st.session_state.get("live_board"),
        sector_summary=st.session_state.get("live_sector_summary"),
    )
    st.session_state["institutional_momentum_score"] = score_result
    score = score_result["score"]
    label = score_result["label"]
    st.metric("Institutional Momentum Score", f"{score:.0f} / 100", label)
    score_frame = pd.DataFrame(
        [{"Component": key, "Score": value} for key, value in score_result["components"].items()]
    )
    st.dataframe(score_frame, use_container_width=True, hide_index=True)
    st.caption(score_result["explanation"])

    momentum_history = append_momentum_snapshot(
        st.session_state.get("institutional_momentum_history"),
        datetime.now(IST),
        score,
        label,
    )
    st.session_state["institutional_momentum_history"] = momentum_history
    if len(momentum_history) >= 2:
        st.caption("Institutional Momentum Score history for the current dashboard session.")
        history_chart = momentum_history.set_index("Timestamp")[["Score"]]
        st.line_chart(history_chart)
        history_display = momentum_history.sort_values("Timestamp", ascending=False).copy()
        history_display["Timestamp"] = history_display["Timestamp"].dt.strftime(
            "%d %b %Y, %H:%M:%S"
        )
        st.dataframe(history_display.head(20), use_container_width=True, hide_index=True)
        st.download_button(
            "Download momentum score history CSV",
            momentum_history.to_csv(index=False).encode("utf-8"),
            file_name="institutional_momentum_history.csv",
            mime="text/csv",
            key="download_institutional_momentum_history",
        )

    st.subheader("🏦 Institutional Flow — FII/FPI & DII")
    st.caption(
        "Latest NSE cash-market institutional activity. NSE states these figures are "
        "provisional and may change after custodial confirmation."
    )
    if st.button("Refresh FII/DII flow", key="refresh_institutional_flow"):
        try:
            flow = fetch_fii_dii_flow()
            st.session_state["institutional_flow"] = flow
            st.session_state["institutional_flow_time"] = datetime.now(IST).strftime(
                "%d %b %Y, %H:%M IST"
            )
        except Exception as exc:
            st.error(f"Institutional flow could not be loaded: {exc}")

    flow = st.session_state.get("institutional_flow")
    if flow is not None and not flow.empty:
        fii = flow[flow["Category"].astype(str).str.contains("FII", case=False, na=False)][
            "Net Value (₹ Cr)"
        ].sum()
        dii = flow[flow["Category"].astype(str).str.contains("DII", case=False, na=False)][
            "Net Value (₹ Cr)"
        ].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("FII/FPI net", f"₹{fii:,.2f} Cr")
        m2.metric("DII net", f"₹{dii:,.2f} Cr")
        m3.metric("Combined net", f"₹{fii + dii:,.2f} Cr")
        st.caption(f"Last updated: {st.session_state.get('institutional_flow_time', 'unknown')}")
        st.dataframe(flow, use_container_width=True, hide_index=True)
        st.download_button(
            "Download FII/DII CSV",
            flow.to_csv(index=False).encode("utf-8"),
            file_name="fii_dii_flow.csv",
            mime="text/csv",
            key="download_institutional_flow",
        )
    else:
        st.info("Click Refresh FII/DII flow during market hours to load the latest NSE data.")

    st.subheader("📅 Institutional Flow History & Trend")
    st.caption(
        "Historical rows exposed by the NSE FII/FPI and DII endpoint. "
        "Use 5, 20, or 60 available sessions for rolling flow context."
    )
    if st.button("Refresh institutional history", key="refresh_institutional_history"):
        try:
            history = fetch_fii_dii_history()
            st.session_state["institutional_flow_history"] = history
            st.session_state["institutional_flow_history_time"] = datetime.now(IST).strftime(
                "%d %b %Y, %H:%M IST"
            )
        except Exception as exc:
            st.error(f"Institutional history could not be loaded: {exc}")

    history = st.session_state.get("institutional_flow_history")
    if history is not None and not history.empty:
        if {"FII Net Value (₹ Cr)", "DII Net Value (₹ Cr)"}.issubset(history.columns):
            trend = history.copy()
            trend["Date"] = pd.to_datetime(trend["Date"], errors="coerce")
            trend = trend.dropna(subset=["Date"]).sort_values("Date", ascending=False)
        else:
            category = history.copy()
            category["Date"] = pd.to_datetime(category["Date"], errors="coerce")
            category = category.dropna(subset=["Date"])
            pivot = category.pivot_table(
                index="Date",
                columns="Category",
                values=[
                    "Buy Value (₹ Cr)",
                    "Sell Value (₹ Cr)",
                    "Net Value (₹ Cr)",
                ],
                aggfunc="sum",
            )
            trend = pd.DataFrame(index=pivot.index)
            for label, category_name in [
                ("FII/FPI", "FII/FPI"),
                ("DII", "DII"),
            ]:
                for metric, short_name in [
                    ("Buy Value (₹ Cr)", "Buy"),
                    ("Sell Value (₹ Cr)", "Sell"),
                    ("Net Value (₹ Cr)", "Net"),
                ]:
                    key = (metric, category_name)
                    if key in pivot.columns:
                        trend[f"{label} {short_name} (₹ Cr)"] = pivot[key]
            trend = trend.reset_index().sort_values("Date", ascending=False)

        if not trend.empty:
            window = st.selectbox(
                "History window",
                [5, 20, 60],
                index=1,
                format_func=lambda value: f"Last {value} available sessions",
                key="institutional_history_window",
            )
            windowed = trend.head(window).copy()
            if "FII Net Value (₹ Cr)" in windowed.columns:
                fii_net = windowed["FII Net Value (₹ Cr)"].sum()
                dii_net = windowed["DII Net Value (₹ Cr)"].sum()
            else:
                fii_net = windowed.get("FII/FPI Net (₹ Cr)", pd.Series(dtype=float)).sum()
                dii_net = windowed.get("DII Net (₹ Cr)", pd.Series(dtype=float)).sum()
            combined_net = fii_net + dii_net
            m1, m2, m3 = st.columns(3)
            m1.metric(f"FII/FPI {window}S net", f"₹{fii_net:,.2f} Cr")
            m2.metric(f"DII {window}S net", f"₹{dii_net:,.2f} Cr")
            m3.metric(f"Combined {window}S net", f"₹{combined_net:,.2f} Cr")

            display = windowed.copy()
            display["Date"] = display["Date"].dt.strftime("%d %b %Y")
            st.dataframe(display, use_container_width=True, hide_index=True)
            chart = windowed.set_index("Date")
            chart_columns = [
                column
                for column in ["FII Net Value (₹ Cr)", "DII Net Value (₹ Cr)"]
                if column in chart.columns
            ]
            if not chart_columns:
                chart_columns = [
                    column
                    for column in ["FII/FPI Net (₹ Cr)", "DII Net (₹ Cr)"]
                    if column in chart.columns
                ]
            if chart_columns:
                st.line_chart(chart[chart_columns].sort_index())
            st.caption(
                f"Last updated: {st.session_state.get('institutional_flow_history_time', 'unknown')}"
            )
            st.download_button(
                "Download institutional history CSV",
                windowed.to_csv(index=False).encode("utf-8"),
                file_name="institutional_flow_history.csv",
                mime="text/csv",
                key="download_institutional_history",
            )
        else:
            st.info("No dated institutional history rows were returned.")
    else:
        st.info("Click Refresh institutional history to load available NSE history.")

    st.divider()

    st.subheader("Unusual activity scanner")
    st.caption(
        "Screens candidate stocks for positive intraday moves and latest 5-minute volume at least 1.5× the average volume of the same time slot in up to four prior sessions. Yahoo Finance coverage and delays may vary."
    )
    exchange_category = st.selectbox(
        "Exchange",
        ["Both", "NSE", "BSE"],
        key="unusual_exchange_category",
        format_func=lambda value: "NSE + BSE" if value == "Both" else value,
    )
    cap_category = st.selectbox(
        "Market-cap basket",
        ["All caps", "Large cap", "Mid cap", "Small cap"],
        key="unusual_cap_category",
    )
    if cap_category == "All caps":
        st.caption(
            "All caps includes the existing NSE and BSE candidate lists. Cap-specific baskets currently screen representative NSE symbols only; they are not exhaustive or official live market-cap classifications."
        )
    else:
        st.caption(
            "Cap-specific baskets screen representative NSE symbols only. BSE scrip codes are not included because the app does not maintain a verified cap-category mapping for them. Constituents and market-cap ranks can change."
        )
    scan_limit = st.selectbox(
        "Maximum results", [10, 20, 30, 50], index=1, key="unusual_scan_limit"
    )
    if st.button("Scan for unusual activity", key="run_unusual_scan"):
        with st.spinner(f"Scanning {exchange_category} · {cap_category.lower()}…"):
            try:
                scan_results = scan_unusual_activity(scan_limit, cap_category, exchange_category)
                st.session_state["unusual_activity_results"] = scan_results
                st.session_state["unusual_activity_scan_category"] = cap_category
                st.session_state["unusual_activity_scan_exchange"] = exchange_category
                st.session_state["unusual_activity_scan_time"] = datetime.now(IST).strftime(
                    "%d %b %Y, %H:%M IST"
                )
            except Exception as exc:
                st.error(f"Scanner could not complete: {exc}")
    scan_results = st.session_state.get("unusual_activity_results")
    if scan_results is not None:
        st.caption(
            f"Last scan: {st.session_state.get('unusual_activity_scan_time', 'unknown')} · Exchange: {st.session_state.get('unusual_activity_scan_exchange', 'unknown')} · Basket: {st.session_state.get('unusual_activity_scan_category', 'unknown')} · Candidate universe is limited; not an exhaustive exchange-wide scan."
        )
        if scan_results.empty:
            st.info(
                "No candidates met the screening conditions, or the data provider returned insufficient data. Try again during market hours."
            )
        else:
            st.dataframe(scan_results, use_container_width=True, hide_index=True)
            st.download_button(
                "Download unusual activity CSV",
                scan_results.to_csv(index=False).encode("utf-8"),
                file_name="unusual_activity.csv",
                mime="text/csv",
                key="download_unusual_activity",
            )

    st.divider()
    left, right = st.columns([2, 1])
    with left:
        symbol = st.text_input(
            "Stock symbol",
            value="RELIANCE",
            help="Enter the NSE/BSE trading symbol without an exchange suffix.",
        )
    with right:
        exchange = st.selectbox("Exchange", ["NSE", "BSE"])
    interval = st.selectbox("Candle timeframe", ["5m", "15m", "30m"], index=1)
    orb_minutes = st.selectbox("Opening range duration", [15, 30], index=0)

    if not st.button("Analyze intraday", type="primary"):
        st.info("Enter a symbol and select Analyze intraday to load recent candles.")
        return
    if not symbol.strip():
        st.warning("Please enter a stock symbol.")
        return

    ticker = _ticker(symbol, exchange)
    with st.spinner(f"Loading recent {interval} candles for {ticker}…"):
        try:
            intraday = yf.download(
                ticker, period="5d", interval=interval, progress=False, auto_adjust=False
            )
            daily = yf.download(
                ticker, period="5d", interval="1d", progress=False, auto_adjust=False
            )
        except Exception as exc:
            st.error(f"Could not retrieve market data: {exc}")
            return
    if intraday is None or intraday.empty:
        st.error(
            "No intraday candles were returned. Verify the symbol/exchange and try again during market hours."
        )
        return
    try:
        data = _prepare(intraday)
    except ValueError as exc:
        st.error(str(exc))
        return
    if data.empty:
        st.error("The provider returned no complete OHLCV candles.")
        return

    timestamp = pd.Timestamp(data.index[-1])
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    timestamp_ist = timestamp.tz_convert(IST)
    now_ist = datetime.now(IST)
    age_minutes = max(0, (now_ist - timestamp_ist.to_pydatetime()).total_seconds() / 60)
    st.caption(
        f"Latest candle: {timestamp_ist:%d %b %Y, %H:%M IST} · Retrieved: {now_ist:%d %b %Y, %H:%M IST}"
    )
    if age_minutes > max(60, int(interval[:-1]) * 3):
        st.warning(
            "Data freshness check: the latest candle is older than expected. This may be normal outside market hours; verify provider timestamps."
        )
    else:
        st.success(
            "Data freshness check: latest candle is recent relative to the selected interval."
        )
    missing = (
        intraday[[c for c in ["Open", "High", "Low", "Close", "Volume"] if c in intraday.columns]]
        .isna()
        .sum()
        .sum()
        if not isinstance(intraday.columns, pd.MultiIndex)
        else 0
    )
    st.caption(
        f"Data quality: {len(data)} complete candles after removing missing OHLCV rows and duplicate timestamps; missing cells detected: {int(missing)}. This does not prove quote accuracy or completeness of the trading session."
    )

    latest = data.iloc[-1]
    metrics = st.columns(4)
    metrics[0].metric("Last close", f"₹{latest['Close']:,.2f}")
    metrics[1].metric("VWAP", f"₹{latest['VWAP']:,.2f}" if pd.notna(latest["VWAP"]) else "—")
    metrics[2].metric("RSI (14)", f"{latest['RSI 14']:.1f}" if pd.notna(latest["RSI 14"]) else "—")
    metrics[3].metric("EMA 9 / 21", f"{latest['EMA 9']:.2f} / {latest['EMA 21']:.2f}")

    bars_needed = max(1, orb_minutes // int(interval[:-1]))
    session_dates = pd.Series(data.index.date, index=data.index)
    today = session_dates.iloc[-1]
    today_data = data.loc[session_dates == today]
    opening = today_data.head(bars_needed)
    st.subheader(f"Opening Range Breakout ({orb_minutes} minutes)")
    if len(opening) < bars_needed:
        st.info(
            f"Opening range is still forming: need {bars_needed} complete {interval} candles; have {len(opening)}."
        )
    else:
        orb_high, orb_low = opening["High"].max(), opening["Low"].min()
        st.caption(
            f"Range high: ₹{orb_high:,.2f} · Range low: ₹{orb_low:,.2f} · Based on first {len(opening)} candles of the latest date in returned data."
        )
        if latest["Close"] > orb_high:
            st.info(
                "Price is above the opening-range high. Treat as a condition to review, not an entry instruction."
            )
        elif latest["Close"] < orb_low:
            st.info(
                "Price is below the opening-range low. Treat as a condition to review, not an entry instruction."
            )
        else:
            st.info("Price remains inside the opening range.")

    if not daily.empty:
        daily_clean = daily.copy()
        if isinstance(daily_clean.columns, pd.MultiIndex):
            daily_clean.columns = daily_clean.columns.get_level_values(0)
        if {"High", "Low", "Close"}.issubset(daily_clean.columns):
            prior = daily_clean.dropna(subset=["High", "Low", "Close"])
            if len(prior) >= 2:
                previous = prior.iloc[-2]
                pivot = (previous["High"] + previous["Low"] + previous["Close"]) / 3
                st.subheader("Previous-session pivot levels")
                p1, p2, p3 = st.columns(3)
                p1.metric("Pivot", f"₹{pivot:,.2f}")
                p2.metric("R1", f"₹{(2 * pivot - previous['Low']):,.2f}")
                p3.metric("S1", f"₹{(2 * pivot - previous['High']):,.2f}")

    bullish = (
        latest["Close"] > latest["VWAP"]
        and latest["EMA 9"] > latest["EMA 21"]
        and latest["MACD"] > latest["MACD signal"]
    )
    bearish = (
        latest["Close"] < latest["VWAP"]
        and latest["EMA 9"] < latest["EMA 21"]
        and latest["MACD"] < latest["MACD signal"]
    )
    st.subheader("Technical conditions (not trade instructions)")
    if bullish:
        st.success(
            "Bullish conditions: close above VWAP, EMA 9 above EMA 21, and MACD above its signal line."
        )
    elif bearish:
        st.warning(
            "Bearish conditions: close below VWAP, EMA 9 below EMA 21, and MACD below its signal line."
        )
    else:
        st.info("Mixed conditions: the selected indicators do not align in one direction.")

    st.subheader("Recent candles and indicators")
    st.line_chart(data[["Close", "VWAP", "EMA 9", "EMA 21"]].tail(120))
    st.line_chart(data[["RSI 14"]].tail(120))
    st.dataframe(data.tail(20).sort_index(ascending=False), use_container_width=True)
    st.download_button(
        "Download analysis CSV",
        data.to_csv().encode("utf-8"),
        file_name=f"{ticker.replace('.', '_')}_{interval}_analysis.csv",
        mime="text/csv",
    )
    st.warning(
        "For education and paper trading only. Indicators can lag; this module does not calculate guaranteed entries, stop-losses, or targets and does not place trades."
    )
