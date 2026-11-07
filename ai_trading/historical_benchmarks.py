"""Historical benchmark matching for completed AI signal observations.

Returns use only benchmark closes observable at signal time and the exact
outcome session. Missing sessions/prices stay explicitly unavailable.
"""
from __future__ import annotations

import math
from datetime import time

import pandas as pd

from scanner.sectors import UNMAPPED, sector_for_ticker

NIFTY_50_TICKER = "^NSEI"
SECTOR_INDEX_TICKERS = {
    "Banks": "^NSEBANK",
    "Financial services": "^CNXFINANCE",
    "IT services": "^CNXIT",
    "Oil, gas & energy": "^CNXENERGY",
    "Metals & mining": "^CNXMETAL",
    "Automobiles": "^CNXAUTO",
    "FMCG": "^CNXFMCG",
    "Healthcare": "^CNXPHARMA",
    "Real estate": "^CNXREALTY",
}


def _session_closes(frame: pd.DataFrame | None) -> pd.Series:
    if frame is None or frame.empty or "Close" not in frame.columns:
        return pd.Series(dtype=float)
    if not isinstance(frame.index, pd.DatetimeIndex):
        return pd.Series(dtype=float)
    values = pd.to_numeric(frame["Close"], errors="coerce")
    values = values.where(values.map(
        lambda value: pd.notna(value) and math.isfinite(float(value)) and float(value) > 0
    )).dropna().sort_index()
    if values.empty:
        return values
    dates = pd.DatetimeIndex(values.index)
    if dates.tz is not None:
        dates = dates.tz_convert("Asia/Kolkata").tz_localize(None)
    values.index = dates.normalize()
    return values.loc[~values.index.duplicated(keep="last")]


def _as_ist(value: object) -> pd.Timestamp | None:
    if value is None or pd.isna(value):
        return None
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        return stamp.tz_localize("Asia/Kolkata")
    return stamp.tz_convert("Asia/Kolkata")


def _benchmark_return(
    closes: pd.Series, signal_timestamp: object, outcome_timestamp: object
) -> tuple[float | None, str]:
    start = _as_ist(signal_timestamp)
    end = _as_ist(outcome_timestamp)
    if start is None or end is None:
        return None, "missing_signal_or_outcome_timestamp"
    if end.normalize() < start.normalize():
        return None, "outcome_precedes_signal"
    # A daily close is not observable before 15:30 IST. Use the previous
    # completed session for intraday signals; use same-day close after market.
    start_date = start.normalize().tz_localize(None)
    if start.time() < time(15, 30):
        eligible = closes.loc[closes.index < start_date]
    else:
        eligible = closes.loc[closes.index <= start_date]
    if eligible.empty:
        return None, "missing_entry_benchmark_close"
    end_date = end.normalize().tz_localize(None)
    if end_date not in closes.index:
        return None, "missing_outcome_benchmark_close"
    entry = float(eligible.iloc[-1])
    exit_price = float(closes.loc[end_date])
    result = (exit_price / entry - 1.0) * 100.0
    if not math.isfinite(result):
        return None, "invalid_benchmark_return"
    return result, "matched"


def attach_historical_benchmarks(
    history: pd.DataFrame,
    benchmark_frames: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Attach NIFTY 50 and mapped sector returns to signal observation windows.

    benchmark_frames is keyed by Yahoo ticker (for example ^NSEI and ^NSEBANK).
    The NIFTY comparison is attempted for every row. Sector comparisons are
    attempted only for stocks with a curated sector-to-index mapping.
    """
    result = history.copy()
    columns = [
        "benchmark_name", "benchmark_return_pct", "benchmark_status",
        "sector", "sector_benchmark_name", "sector_benchmark_return_pct",
        "sector_benchmark_status",
    ]
    if result.empty:
        for column in columns:
            if column not in result:
                result[column] = pd.Series(dtype="object")
        return result
    if not {"timestamp", "outcome_timestamp", "symbol"}.issubset(result.columns):
        raise ValueError(
            "Signal history requires timestamp, outcome_timestamp and symbol columns"
        )

    close_cache = {ticker: _session_closes(frame) for ticker, frame in benchmark_frames.items()}
    nifty = close_cache.get(NIFTY_50_TICKER, pd.Series(dtype=float))
    values: list[dict[str, object]] = []
    for row in result.itertuples(index=False):
        nifty_return, nifty_status = _benchmark_return(
            nifty, row.timestamp, row.outcome_timestamp
        )
        sector = sector_for_ticker(str(row.symbol))
        sector_ticker = SECTOR_INDEX_TICKERS.get(sector)
        sector_return: float | None = None
        sector_status = "sector_index_not_mapped"
        if sector_ticker:
            sector_return, sector_status = _benchmark_return(
                close_cache.get(sector_ticker, pd.Series(dtype=float)),
                row.timestamp,
                row.outcome_timestamp,
            )
        values.append({
            "benchmark_name": "NIFTY 50",
            "benchmark_return_pct": nifty_return,
            "benchmark_status": (
                nifty_status if NIFTY_50_TICKER in close_cache else "benchmark_data_unavailable"
            ),
            "sector": sector,
            "sector_benchmark_name": sector_ticker or pd.NA,
            "sector_benchmark_return_pct": sector_return,
            "sector_benchmark_status": sector_status if sector_ticker else (
                "sector_unmapped" if sector == UNMAPPED else sector_status
            ),
        })
    attached = pd.DataFrame(values, index=result.index)
    for column in columns:
        result[column] = attached[column]
    return result
