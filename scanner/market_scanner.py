import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

from ai_trading.momentum_scoring import score_momentum
from engine.breakout_engine import detect_breakout
from engine.signal_engine import generate_signal
from indicators.atr import calculate_atr
from indicators.bollinger import calculate_bollinger
from indicators.macd import calculate_macd
from indicators.macd_histogram import calculate_histogram
from indicators.moving_average import calculate_ema, calculate_sma
from indicators.rsi import calculate_rsi
from indicators.support_resistance import calculate_support_resistance
from indicators.trend import detect_trend
from scanner.dynamic_universe import (
    merge_bse_universe,
    merge_nse_universe,
)
from services.data_quality import last_bar_date, split_stale
from services.sector_mapping import sector_for_symbol

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

TOP_CANDIDATES_TO_ANALYZE = 20
DISPLAY_COUNT = 20
DOWNLOAD_CHUNK_SIZE = 40
MAX_CANDIDATES_PER_EXCHANGE = 10
ANALYSIS_PERIOD = "1y"


def _ticker(symbol: str, exchange: str) -> str:
    suffix = "NS" if exchange == "NSE" else "BO"
    return f"{symbol}.{suffix}"


def _extract_series(history: pd.DataFrame, ticker: str, field: str) -> pd.Series:
    """Extract a field from either yfinance MultiIndex column orientation."""
    if not isinstance(history.columns, pd.MultiIndex):
        return pd.to_numeric(history[field], errors="coerce").dropna()

    levels = history.columns
    for level in range(levels.nlevels):
        if ticker in levels.get_level_values(level):
            frame = history.xs(ticker, axis=1, level=level)
            if field in frame.columns:
                return pd.to_numeric(frame[field], errors="coerce").dropna()

    return pd.Series(dtype="float64")


def _extract_history_frame(history: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Extract one ticker's OHLCV frame from a yfinance batch response."""
    if history.empty:
        return pd.DataFrame()

    if not isinstance(history.columns, pd.MultiIndex):
        frame = history.copy()
    else:
        frame = pd.DataFrame()
        levels = history.columns
        for level in range(levels.nlevels):
            if ticker in levels.get_level_values(level):
                frame = history.xs(ticker, axis=1, level=level).copy()
                break

    required = ["Open", "High", "Low", "Close", "Volume"]
    if frame.empty or any(column not in frame.columns for column in required):
        return pd.DataFrame()

    frame = frame.loc[:, required].apply(pd.to_numeric, errors="coerce")
    return frame.dropna(subset=required)


def _download_chunk(chunk: list[str]) -> pd.DataFrame:
    """Download a mover-screen chunk, retrying once without threading."""
    try:
        history = yf.download(
            tickers=chunk,
            period="5d",
            interval="1d",
            auto_adjust=True,
            progress=False,
            group_by="ticker",
            threads=True,
            timeout=10,
        )
        if history is not None and not history.empty:
            return history
    except Exception as exc:
        logger.debug(
            "Price download attempt failed, retrying single-threaded (%d symbols, first: %s): %s",
            len(chunk),
            chunk[0] if chunk else "-",
            exc,
        )

    try:
        history = yf.download(
            tickers=chunk,
            period="5d",
            interval="1d",
            auto_adjust=True,
            progress=False,
            group_by="ticker",
            threads=False,
            timeout=15,
        )
    except Exception as exc:
        logger.warning(
            "Price download failed for a chunk of %d symbols (first: %s): %s",
            len(chunk),
            chunk[0] if chunk else "-",
            exc,
        )
        return pd.DataFrame()
    return history if history is not None else pd.DataFrame()


def _download_analysis_chunk(chunk: list[str]) -> pd.DataFrame:
    """Download the full history for shortlisted tickers in one batch."""
    try:
        history = yf.download(
            tickers=chunk,
            period=ANALYSIS_PERIOD,
            interval="1d",
            auto_adjust=True,
            progress=False,
            group_by="ticker",
            threads=True,
            timeout=15,
        )
        if history is not None and not history.empty:
            return history
    except Exception as exc:
        logger.debug(
            "Price download attempt failed, retrying single-threaded (%d symbols, first: %s): %s",
            len(chunk),
            chunk[0] if chunk else "-",
            exc,
        )

    try:
        history = yf.download(
            tickers=chunk,
            period=ANALYSIS_PERIOD,
            interval="1d",
            auto_adjust=True,
            progress=False,
            group_by="ticker",
            threads=False,
            timeout=20,
        )
    except Exception as exc:
        logger.warning(
            "Price download failed for a chunk of %d symbols (first: %s): %s",
            len(chunk),
            chunk[0] if chunk else "-",
            exc,
        )
        return pd.DataFrame()
    return history if history is not None else pd.DataFrame()


def _batch_change_screen(
    candidates: dict[str, list[str]],
) -> list[tuple[str, str, float, float]]:
    """Find price movers across the current NSE and BSE universes without a liquidity exclusion."""
    ranked: list[tuple[str, str, float, float]] = []
    series_by_ticker: dict[str, tuple[str, pd.Series, pd.Series]] = {}

    for exchange, symbols in candidates.items():
        tickers = [_ticker(symbol, exchange) for symbol in symbols]
        for start in range(0, len(tickers), DOWNLOAD_CHUNK_SIZE):
            chunk = tickers[start : start + DOWNLOAD_CHUNK_SIZE]
            history = _download_chunk(chunk)
            if history.empty:
                continue

            for ticker in chunk:
                try:
                    close = _extract_series(history, ticker, "Close")
                    volume = _extract_series(history, ticker, "Volume")
                except (KeyError, TypeError, ValueError, IndexError):
                    continue
                if len(close) < 2 or volume.empty:
                    continue
                series_by_ticker[ticker] = (exchange, close, volume)

    # A halted or suspended name keeps an old last bar. Rank only tickers on the most
    # recent session seen across the whole universe so stale moves are not shown as current.
    reference, stale = split_stale(
        {ticker: last_bar_date(close) for ticker, (_ex, close, _vol) in series_by_ticker.items()},
        today=datetime.now(IST).date(),
    )
    if stale:
        logger.warning(
            "Excluded %d of %d tickers whose last bar is not the latest session (%s); first: %s",
            len(stale),
            len(series_by_ticker),
            reference,
            ", ".join(stale[:5]),
        )
    stale_set = set(stale)

    for ticker, (exchange, close, volume) in series_by_ticker.items():
        if ticker in stale_set:
            continue
        try:
            latest = float(close.iloc[-1])
            previous = float(close.iloc[-2])
            average_volume = float(volume.tail(5).mean())
            if previous == 0:
                continue

            change_pct = ((latest - previous) / previous) * 100
            average_turnover = latest * average_volume
            ranked.append((ticker, exchange, change_pct, average_turnover))
        except (TypeError, ValueError, IndexError):
            continue

    ranked.sort(key=lambda row: abs(row[2]), reverse=True)
    return ranked


def _momentum_components(df: pd.DataFrame) -> dict[str, float | None]:
    """Convert recent OHLCV context into bounded, explainable momentum components."""
    if len(df) < 21:
        return {
            "trend": None,
            "relative_strength": None,
            "volume_expansion": None,
            "breakout_quality": None,
        }

    last = df.iloc[-1]
    close = float(last["Close"])
    sma20 = float(last["SMA_20"])
    sma50 = float(last["SMA_50"])
    prior_close = float(df["Close"].iloc[-21])
    average_volume = float(df["Volume"].tail(20).mean())
    latest_volume = float(last["Volume"])
    high_20 = float(df["High"].tail(20).max())

    trend_score = (
        100.0
        if close >= sma20 and close >= sma50
        else 50.0
        if close >= sma20 or close >= sma50
        else 0.0
    )
    return_pct = ((close / prior_close) - 1.0) * 100 if prior_close > 0 else 0.0
    relative_strength_score = max(0.0, min(100.0, (return_pct + 10.0) * 5.0))
    volume_ratio = latest_volume / average_volume if average_volume > 0 else None
    volume_score = (
        max(0.0, min(100.0, (volume_ratio - 0.5) * (100.0 / 1.5)))
        if volume_ratio is not None
        else None
    )
    breakout_score = (
        max(0.0, min(100.0, (close / high_20) * 100.0))
        if high_20 > 0
        else None
    )
    return {
        "trend": trend_score,
        "relative_strength": relative_strength_score,
        "volume_expansion": volume_score,
        "breakout_quality": breakout_score,
    }


def _analyze_history(
    ticker: str,
    history: pd.DataFrame,
    average_turnover: float | None = None,
) -> dict[str, Any] | None:
    """Run the scanner's technical analysis locally on already-downloaded data."""
    df = _extract_history_frame(history, ticker)
    if len(df) < 50:
        return None

    try:
        # Capture the last bar's date before the index is dropped so every row says which
        # session its price comes from (None when the frame has no date index).
        as_of = last_bar_date(df)
        df = df.reset_index(drop=True)
        df = calculate_sma(df, 20)
        df = calculate_sma(df, 50)
        df = calculate_ema(df, 20)
        df = calculate_rsi(df, 14)
        df = calculate_macd(df)
        df = calculate_histogram(df)
        df = calculate_bollinger(df)
        df = calculate_atr(df)
        df = calculate_support_resistance(df, 10)

        trend = detect_trend(df)
        signal = generate_signal(df)
        detect_breakout(df)

        if signal.get("Status") != "OK":
            return None

        last = df.iloc[-1]
        momentum = score_momentum(_momentum_components(df))
        exchange = "BSE" if ticker.endswith(".BO") else "NSE"
        symbol = ticker.removesuffix(".NS").removesuffix(".BO")
        return {
            "Symbol": symbol,
            "Exchange": exchange,
            "Sector": sector_for_symbol(symbol),
            "Price": round(float(last["Close"]), 2),
            "Data As Of": as_of.isoformat() if as_of is not None else None,
            "Avg Turnover (₹)": (
                round(average_turnover, 0) if average_turnover is not None else None
            ),
            "Trend": trend["Trend"],
            "RSI": round(float(last["RSI_14"]), 2),
            "MACD": round(float(last["MACD"]), 2),
            "ATR": round(float(last["ATR"]), 2),
            "AI Score": signal["Score"],
            "Momentum Score": momentum.score,
            "Momentum Explanation": momentum.explanation,
            "Confidence": signal["Confidence"],
            "Risk": signal.get("Risk", "Medium"),
            "Recommendation": signal["Recommendation"],
        }
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def market_scan(exchange_filter: str = "NSE + BSE") -> pd.DataFrame:
    """Scan the selected exchange universe using batched market data and local analysis."""
    selected = exchange_filter.strip().upper()
    candidates = {}
    if selected in ("NSE", "NSE + BSE", "BOTH"):
        candidates["NSE"] = merge_nse_universe()
    if selected in ("BSE", "NSE + BSE", "BOTH"):
        candidates["BSE"] = merge_bse_universe()
    if not candidates:
        raise ValueError(f"Unsupported exchange filter: {exchange_filter}")
    coverage = {
        exchange: {
            "candidates": len(symbols),
            "tickers_requested": len(symbols),
            "histories_returned": 0,
            "histories_rejected": 0,
            "analyses_completed": 0,
            "final_rows": 0,
        }
        for exchange, symbols in candidates.items()
    }
    coverage_by_ticker = {
        _ticker(symbol, exchange): exchange
        for exchange, symbols in candidates.items()
        for symbol in symbols
    }
    movers = _batch_change_screen(candidates)
    for _ticker_value, exchange, _change, _turnover in movers:
        if exchange in coverage:
            coverage[exchange]["histories_returned"] += 1
    for exchange in coverage:
        coverage[exchange]["histories_rejected"] = max(
            0, coverage[exchange]["candidates"] - coverage[exchange]["histories_returned"]
        )
    if not movers:
        empty = pd.DataFrame()
        empty.attrs["scanner_coverage"] = coverage
        return empty

    analysis_tickers: list[str] = []
    seen: set[str] = set()
    exchange_counts = {"NSE": 0, "BSE": 0}
    for ticker, exchange, _change, _turnover in movers:
        if ticker in seen or exchange_counts[exchange] >= MAX_CANDIDATES_PER_EXCHANGE:
            continue
        analysis_tickers.append(ticker)
        seen.add(ticker)
        exchange_counts[exchange] += 1
        if len(analysis_tickers) >= TOP_CANDIDATES_TO_ANALYZE:
            break

    for ticker in analysis_tickers:
        exchange = coverage_by_ticker.get(ticker)
        if exchange in coverage:
            coverage[exchange]["analysis_requested"] = (
                coverage[exchange].get("analysis_requested", 0) + 1
            )
    if not analysis_tickers:
        empty = pd.DataFrame()
        empty.attrs["scanner_coverage"] = coverage
        return empty

    history = _download_analysis_chunk(analysis_tickers)
    if history.empty:
        empty = pd.DataFrame()
        empty.attrs["scanner_coverage"] = coverage
        return empty

    turnover_by_ticker = {ticker: turnover for ticker, _exchange, _change, turnover in movers}

    rows: list[dict[str, Any]] = []
    for ticker in analysis_tickers:
        row = _analyze_history(ticker, history, turnover_by_ticker.get(ticker))
        exchange = coverage_by_ticker.get(ticker)
        if row is not None:
            rows.append(row)
            if exchange in coverage:
                coverage[exchange]["analyses_completed"] += 1

    df = pd.DataFrame(rows)
    if df.empty:
        df.attrs["scanner_coverage"] = coverage
        return df

    result = (
        df.sort_values(by=["AI Score", "Confidence"], ascending=[False, False])
        .head(DISPLAY_COUNT)
        .reset_index(drop=True)
    )
    for exchange in coverage:
        coverage[exchange]["final_rows"] = int((result["Exchange"] == exchange).sum())
    result.attrs["scanner_coverage"] = coverage
    return result
