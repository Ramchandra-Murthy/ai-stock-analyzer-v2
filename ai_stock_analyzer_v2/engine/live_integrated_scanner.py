"""Refreshing multi-symbol scanner for the integrated Chapter 4-10 workflow."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pandas as pd
import yfinance as yf

from engine.trading_pipeline import integrated_trade_frame

DEFAULT_TICKERS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "AXISBANK.NS",
    "HINDUNILVR.NS",
    "LT.NS",
    "BHARTIARTL.NS",
]


def _download(
    tickers: Sequence[str],
    *,
    period: str,
    interval: str,
) -> pd.DataFrame:
    """Download a batch of ticker histories from yfinance."""
    return yf.download(
        tickers=list(tickers),
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        group_by="ticker",
        threads=True,
        timeout=10,
    )


def _symbol_frame(history: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Extract one ticker's OHLC history from a yfinance batch response."""
    if history.empty:
        return pd.DataFrame()

    if not isinstance(history.columns, pd.MultiIndex):
        return history.copy()

    levels = history.columns.get_level_values(0)
    if ticker in levels:
        return history[ticker].copy()

    fields = {"Open", "High", "Low", "Close", "Volume"}
    if fields.intersection(set(levels)):
        return history.xs(ticker, axis=1, level=1).copy()

    return pd.DataFrame()


def scan_integrated_tickers(
    tickers: Sequence[str],
    *,
    period: str = "6mo",
    interval: str = "1d",
    fast_period: int = 20,
    slow_period: int = 50,
    downloader: Callable[..., pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Return the latest integrated signal for each supplied ticker.

    The scanner is analytics-only: it reports price, regime, regime score,
    edge signal, and direction. It never sizes or places a trade.
    """
    symbols = list(dict.fromkeys(symbol.strip().upper() for symbol in tickers if symbol.strip()))
    columns = [
        "Ticker",
        "Close",
        "Regime",
        "Regime Score",
        "Edge Signal",
        "Direction",
    ]
    if not symbols:
        return pd.DataFrame(columns=columns)

    fetch = downloader or _download
    try:
        history = fetch(symbols, period=period, interval=interval)
    except Exception:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []
    for ticker in symbols:
        prices = _symbol_frame(history, ticker)
        if prices.empty:
            continue

        try:
            workflow = integrated_trade_frame(
                prices,
                fast_period=fast_period,
                slow_period=slow_period,
            )
            latest = workflow.iloc[-1]
            close = float(latest["close"])
            if pd.isna(close):
                continue
            edge = float(latest["edge_signal"])
            rows.append(
                {
                    "Ticker": ticker,
                    "Close": round(close, 2),
                    "Regime": str(latest["regime"]),
                    "Regime Score": round(float(latest["regime_score"]), 2),
                    "Edge Signal": round(edge, 2),
                    "Direction": ("LONG" if edge > 0 else "SHORT" if edge < 0 else "FLAT"),
                }
            )
        except (KeyError, ValueError, TypeError, IndexError):
            continue

    return pd.DataFrame(rows, columns=columns)
