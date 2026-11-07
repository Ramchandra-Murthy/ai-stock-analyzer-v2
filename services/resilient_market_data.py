"""Resilient Yahoo Finance market-data retrieval helpers.

These helpers keep provider failures explicit. They retry transient failures,
fall back to per-symbol retrieval for missing tickers, and never fabricate data.
They are intended for research/paper-trading workflows; Yahoo Finance is not an
exchange-tick execution feed.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from time import sleep
from typing import Any

import pandas as pd
import yfinance as yf

from services.cached_download import cached_download
from services.ohlcv_validation import build_data_status, validate_ohlcv_frame

DEFAULT_RETRIES = 2
DEFAULT_TIMEOUT = 12.0
RETRY_BACKOFF_SECONDS = 1.0


def _ticker_frame(history: pd.DataFrame | None, ticker: str) -> pd.DataFrame:
    """Extract one ticker from either supported yfinance column layout."""
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

    if frame.empty:
        return pd.DataFrame()

    frame = frame.loc[:, ~frame.columns.duplicated()].copy()
    if "Close" not in frame.columns:
        return pd.DataFrame()
    return frame.dropna(how="all").sort_index()


def _cached_yfinance_download(tickers: list[str], *, period: str, **kwargs: Any) -> pd.DataFrame:
    """Stable downloader identity for shared successful-batch caching."""
    return yf.download(tickers=tickers, period=period, **kwargs)


def _download_batch(
    tickers: list[str],
    *,
    period: str,
    interval: str,
    auto_adjust: bool,
    timeout: float,
    retries: int = DEFAULT_RETRIES,
    diagnostics: list[str] | None = None,
) -> pd.DataFrame:
    """Download one batch with bounded retries and no hidden synthetic data."""
    last_error: Exception | None = None

    retry_count = max(0, int(retries))
    for attempt in range(retry_count + 1):
        try:
            result = cached_download(
                tickers,
                period=period,
                ttl=900.0,
                cache_empty=False,
                downloader=_cached_yfinance_download,
                interval=interval,
                auto_adjust=auto_adjust,
                progress=False,
                group_by="ticker",
                threads=False,
                timeout=timeout,
                repair=True,
            )
            if result is not None and not result.empty:
                return result
        except Exception as exc:
            last_error = exc
            if diagnostics is not None:
                diagnostics.append(f"batch request raised {type(exc).__name__}")
        else:
            if diagnostics is not None and (result is None or result.empty):
                diagnostics.append("batch request returned no rows")

        if attempt < retry_count:
            sleep(RETRY_BACKOFF_SECONDS * (2**attempt))

    if last_error is not None:
        return pd.DataFrame()
    return pd.DataFrame()


def _download_single(
    ticker: str,
    *,
    period: str,
    interval: str,
    auto_adjust: bool,
    timeout: float,
    retries: int = DEFAULT_RETRIES,
    diagnostics: list[str] | None = None,
) -> pd.DataFrame:
    """Recover one missing ticker through the direct Ticker.history endpoint."""
    retry_count = max(0, int(retries))
    for attempt in range(retry_count + 1):
        try:
            result = yf.Ticker(ticker).history(
                period=period,
                interval=interval,
                auto_adjust=auto_adjust,
                timeout=timeout,
                repair=True,
                raise_errors=False,
            )
            frame = _ticker_frame(result, ticker)
            if not frame.empty:
                return frame
        except Exception as exc:
            if diagnostics is not None:
                diagnostics.append(f"single-symbol request raised {type(exc).__name__}")
        if attempt < retry_count:
            sleep(RETRY_BACKOFF_SECONDS * (2**attempt))
    return pd.DataFrame()


def download_symbols_individually(
    tickers: Iterable[str],
    *,
    period: str,
    interval: str,
    auto_adjust: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    max_symbols: int | None = None,
    diagnostics: list[str] | None = None,
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Recover tickers one request at a time, with a hard cap on requests.

    Unlike ``download_symbol_frames(recover_missing=True)`` this does not issue a
    batch request first, so callers that already tried a batch do not repeat it.
    At most ``max_symbols`` tickers are attempted and each is tried
    ``retries + 1`` times; the remainder is reported as unresolved, never
    fabricated.
    """
    symbols = list(dict.fromkeys(str(t).strip().upper() for t in tickers if str(t).strip()))
    attempted = symbols if max_symbols is None else symbols[: max(0, int(max_symbols))]

    frames: dict[str, pd.DataFrame] = {}
    for ticker in attempted:
        frame = _download_single(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=auto_adjust,
            timeout=timeout,
            retries=retries,
            diagnostics=diagnostics,
        )
        if not frame.empty:
            frames[ticker] = frame

    return frames, [ticker for ticker in symbols if ticker not in frames]


def download_symbol_frames(
    tickers: Iterable[str],
    *,
    period: str,
    interval: str,
    auto_adjust: bool = False,
    batch_size: int = 10,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    recover_missing: bool = True,
    diagnostics: list[str] | None = None,
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Return usable ticker frames plus an explicit list of unresolved tickers."""
    symbols = list(dict.fromkeys(str(t).strip().upper() for t in tickers if str(t).strip()))
    if not symbols:
        return {}, []

    frames: dict[str, pd.DataFrame] = {}
    for start in range(0, len(symbols), max(1, int(batch_size))):
        chunk = symbols[start : start + max(1, int(batch_size))]
        history = _download_batch(
            chunk,
            period=period,
            interval=interval,
            auto_adjust=auto_adjust,
            timeout=timeout,
            retries=retries,
            diagnostics=diagnostics,
        )
        for ticker in chunk:
            frame = _ticker_frame(history, ticker)
            if not frame.empty:
                frames[ticker] = frame

    missing = [ticker for ticker in symbols if ticker not in frames]
    if recover_missing:
        for ticker in missing:
            frame = _download_single(
                ticker,
                period=period,
                interval=interval,
                auto_adjust=auto_adjust,
                timeout=timeout,
                retries=retries,
                diagnostics=diagnostics,
            )
            if not frame.empty:
                frames[ticker] = frame

    return frames, [ticker for ticker in symbols if ticker not in frames]


def download_market_frames(
    tickers: Iterable[str],
    *,
    period: str,
    interval: str,
    auto_adjust: bool = False,
    batch_size: int = 10,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    recover_missing: bool = True,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    """Download frames with diagnostics suitable for scanner health reporting."""
    symbols = list(dict.fromkeys(str(t).strip().upper() for t in tickers if str(t).strip()))
    diagnostics: list[str] = []
    frames, missing = download_symbol_frames(
        symbols,
        period=period,
        interval=interval,
        auto_adjust=auto_adjust,
        batch_size=batch_size,
        timeout=timeout,
        retries=retries,
        recover_missing=recover_missing,
        diagnostics=diagnostics,
    )
    retrieved_at = datetime.now(UTC)
    data_status: dict[str, dict[str, Any]] = {}
    invalid: list[str] = []
    for ticker, frame in list(frames.items()):
        validated, errors = validate_ohlcv_frame(frame)
        data_status[ticker] = build_data_status(
            validated if not errors else frame,
            source="Yahoo Finance",
            retrieved_at=retrieved_at,
            errors=errors,
        )
        if errors:
            invalid.append(ticker)
            frames.pop(ticker, None)
        else:
            frames[ticker] = validated
    missing = sorted(set(missing).union(invalid))
    return frames, {
        "source": "Yahoo Finance",
        "retrieved_at": retrieved_at.isoformat(),
        "requested": len(symbols),
        "usable": len(frames),
        "missing": missing,
        "invalid": invalid,
        "data_status": data_status,
        "coverage_pct": round(len(frames) / len(symbols) * 100, 1) if symbols else 100.0,
        "complete": not missing,
        "failure_diagnostics": list(dict.fromkeys(diagnostics)),
    }
