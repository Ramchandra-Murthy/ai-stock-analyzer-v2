"""Fast live Top-10 market-mover scanner with one-minute refresh."""

# The fast path scans a balanced, bounded NSE/BSE pool to keep live refresh latency bounded.

from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from time import perf_counter
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES
from services.dhan_live_provider import dhan_provider_enabled, download_dhan_symbol_frames
from services.resilient_market_data import download_symbol_frames, download_symbols_individually

logger = logging.getLogger(__name__)

TOP10_REFRESH_SECONDS = 60
TOP10_UI_POLL_SECONDS = 2
TOP10_CACHE_SECONDS = 50
TOP10_TIMEZONE = "Asia/Kolkata"
TOP10_CHUNK_SIZE = 10
TOP10_MAX_NSE_CANDIDATES = 10
TOP10_MAX_BSE_CANDIDATES = 10
TOP10_PROVIDER_RETRIES = 0
TOP10_PROVIDER_TIMEOUT = 5
# Bounded recovery for symbols the first batch pass could not resolve.
TOP10_FALLBACK_CHUNK_SIZE = 5
TOP10_FALLBACK_TIMEOUT = 4
TOP10_MAX_SINGLE_SYMBOL_RECOVERY = 4
TOP10_SCAN_BUDGET_SECONDS = 30
# A scan still running after this long is abandoned so the page cannot refresh forever.
TOP10_SCAN_HARD_TIMEOUT_SECONDS = 90
# Failed scans are retried with exponential backoff, never more often than this.
TOP10_RETRY_BACKOFF_SECONDS = 15
TOP10_RETRY_BACKOFF_MAX_SECONDS = 60
TOP10_MANUAL_REFRESH_MIN_SECONDS = 5
TOP10_MAX_CONSECUTIVE_FAILURES = 2
TOP10_SCAN_WARNING_SECONDS = 20
TOP10_STALE_DATA_SECONDS = 180
TOP10_MARKET_OPEN_HOUR = 9
TOP10_MARKET_OPEN_MINUTE = 15
TOP10_MARKET_CLOSE_HOUR = 15
TOP10_MARKET_CLOSE_MINUTE = 30
TOP10_SESSION_STATUS_KEY = "top10_market_status"
TOP10_PARTIAL_FAILURES_KEY = "top10_partial_failures"
TOP10_COVERAGE_KEY = "top10_quote_coverage"
TOP10_SEEN_GENERATION_KEY = "top10_seen_scan_generation"
TOP10_EXPECTED_QUOTES = 20
TOP10_GOOD_COVERAGE_QUOTES = 18
TOP10_REDUCED_COVERAGE_QUOTES = 10
TOP10_MIN_TRUSTED_COVERAGE_QUOTES = 18
TOP10_ALERT_MIN_RANK_JUMP = 2
TOP10_ALERT_MIN_ABS_MOVE_PCT = 1.0
TOP10_SCORE_MAX_1M_PCT = 3.0
TOP10_SCORE_MAX_5M_PCT = 5.0
TOP10_SCORE_MAX_RANK_JUMP = 5
TOP10_SIGNAL_HISTORY_LIMIT = 10
TOP10_SIGNAL_HISTORY_KEY = "top10_signal_history"
TOP10_SIGNAL_HISTORY_UPDATED_KEY = "top10_signal_history_updated_at"
TOP10_PERSISTENCE_MIN_SCANS = 2
TOP10_PERSISTENCE_ALERT_MIN_SCANS = 3
_IST = ZoneInfo(TOP10_TIMEZONE)

_SCAN_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="top10-scan")
_SCAN_LOCK = Lock()
_SCAN_FUTURE: Future[tuple[pd.DataFrame, float, int, int]] | None = None
# The last *successful* scan; a failed refresh never clears it.
_SCAN_RESULT: tuple[pd.DataFrame, float, int, int] | None = None
_SCAN_FAILURES = 0
_SCAN_COMPLETED_AT: datetime | None = None
_SCAN_GENERATION = 0
_SCAN_LAST_ERROR: str | None = None
_SCAN_NEXT_ATTEMPT_AT: datetime | None = None
_SCAN_STARTED_AT: datetime | None = None
# When the worker really finished, so polling jitter never shifts the refresh cadence.
_SCAN_FINISHED_AT: datetime | None = None
_SCAN_TOKEN = 0
# Working list for the scan in progress, and the settled copy shown in the UI.
_PROVIDER_DIAGNOSTICS: list[str] = []
_LAST_SCAN_DIAGNOSTICS: list[str] = []


def _market_is_open(now: datetime) -> bool:
    """Return whether the NSE/BSE regular session is open in India."""
    if now.weekday() >= 5:
        return False
    market_open = now.replace(
        hour=TOP10_MARKET_OPEN_HOUR,
        minute=TOP10_MARKET_OPEN_MINUTE,
        second=0,
        microsecond=0,
    )
    market_close = now.replace(
        hour=TOP10_MARKET_CLOSE_HOUR,
        minute=TOP10_MARKET_CLOSE_MINUTE,
        second=0,
        microsecond=0,
    )
    return market_open <= now <= market_close


def _ticker(symbol: str, exchange: str) -> str:
    suffix = ".NS" if exchange == "NSE" else ".BO"
    cleaned = str(symbol).strip().upper()
    return cleaned if cleaned.endswith((".NS", ".BO")) else f"{cleaned}{suffix}"


def _extract_close(history: pd.DataFrame, ticker: str) -> pd.Series:
    """Extract one ticker's Close series from either yfinance layout."""
    if history is None or history.empty:
        return pd.Series(dtype="float64")

    if not isinstance(history.columns, pd.MultiIndex):
        if "Close" not in history.columns:
            return pd.Series(dtype="float64")
        return pd.to_numeric(history["Close"], errors="coerce").dropna()

    for level in range(history.columns.nlevels):
        values = history.columns.get_level_values(level)
        if ticker in values:
            frame = history.xs(ticker, axis=1, level=level)
            if "Close" in frame.columns:
                return pd.to_numeric(frame["Close"], errors="coerce").dropna()

    return pd.Series(dtype="float64")


def _provider_age_seconds(timestamp: object, now: datetime) -> float | None:
    """Return provider-candle age in seconds, or None when invalid."""
    try:
        value = pd.Timestamp(timestamp)
        if value.tzinfo is None:
            value = value.tz_localize(_IST)
        else:
            value = value.tz_convert(_IST)
        age_seconds = (now - value.to_pydatetime()).total_seconds()
        # A future-dated candle is not fresh data; reject clock/provider anomalies.
        return age_seconds if age_seconds >= 0 else None
    except (TypeError, ValueError):
        return None


def _is_fresh_provider_timestamp(timestamp: object, now: datetime) -> bool:
    """Return whether a candle timestamp is known and within the scanner freshness limit."""
    age_seconds = _provider_age_seconds(timestamp, now)
    return age_seconds is not None and age_seconds < TOP10_STALE_DATA_SECONDS


def _format_candle_time(timestamp: object) -> str:
    """Format a provider candle timestamp in India time for the live table."""
    try:
        value = pd.Timestamp(timestamp)
        if value.tzinfo is None:
            value = value.tz_localize(_IST)
        return value.tz_convert(_IST).strftime("%Y-%m-%d %H:%M:%S IST")
    except (TypeError, ValueError):
        return str(timestamp)


def _coverage_status(valid_quotes: int) -> str:
    """Classify quote coverage without changing ranking or scan selection."""
    if valid_quotes >= TOP10_GOOD_COVERAGE_QUOTES:
        return "GOOD"
    if valid_quotes >= TOP10_REDUCED_COVERAGE_QUOTES:
        return "REDUCED"
    return "CRITICAL"


def _annotate_watchlist_changes(
    current: pd.DataFrame,
    previous: pd.DataFrame | None,
) -> tuple[pd.DataFrame, list[str]]:
    """Add one-minute watchlist membership/rank changes to the current Top-10."""
    if current.empty:
        return current.copy(), []

    annotated = current.copy()
    previous = previous if previous is not None else pd.DataFrame()
    previous_keys = (
        set(zip(previous["Exchange"], previous["Symbol"], strict=True))
        if {"Exchange", "Symbol"}.issubset(previous.columns)
        else set()
    )
    previous_ranks = (
        {(row["Exchange"], row["Symbol"]): int(row["Rank"]) for row in previous.to_dict("records")}
        if {"Exchange", "Symbol", "Rank"}.issubset(previous.columns)
        else {}
    )

    statuses: list[str] = []
    rank_changes: list[int | None] = []
    current_keys = set()

    for row in annotated.to_dict("records"):
        key = (row["Exchange"], row["Symbol"])
        current_keys.add(key)
        if key not in previous_keys:
            statuses.append("NEW")
            rank_changes.append(None)
            continue
        rank_change = previous_ranks[key] - int(row["Rank"])
        rank_changes.append(rank_change)
        statuses.append("UP" if rank_change > 0 else "DOWN" if rank_change < 0 else "UNCHANGED")

    annotated.insert(0, "Status", statuses)
    annotated.insert(
        1,
        "Rank change",
        pd.Series(rank_changes, index=annotated.index, dtype=object),
    )
    dropped = [f"{exchange}:{symbol}" for exchange, symbol in sorted(previous_keys - current_keys)]
    return annotated, dropped


def _watchlist_change_alerts(annotated: pd.DataFrame) -> list[str]:
    """Build concise alerts for material Top-10 membership, rank, or move changes."""
    if annotated.empty:
        return []

    alerts: list[str] = []
    for row in annotated.to_dict("records"):
        symbol = f"{row['Exchange']}:{row['Symbol']}"
        status = str(row["Status"])
        rank_change = row.get("Rank change")
        move = float(row.get("1-min %", 0.0) or 0.0)

        if status == "NEW":
            alerts.append(f"🆕 NEW · {symbol} entered Top-10 · 1-min {move:+.2f}%")
        elif rank_change is not None and abs(int(rank_change)) >= TOP10_ALERT_MIN_RANK_JUMP:
            direction = "up" if int(rank_change) > 0 else "down"
            alerts.append(
                f"🔔 RANK {direction.upper()} · {symbol} · {abs(int(rank_change))} places · "
                f"1-min {move:+.2f}%"
            )
        elif abs(move) >= TOP10_ALERT_MIN_ABS_MOVE_PCT:
            alerts.append(f"⚡ MOVE · {symbol} · 1-min {move:+.2f}%")

    return alerts


def _calculate_signal_strength(row: dict[str, object]) -> tuple[int, str]:
    """Calculate a transparent 0-100 momentum score and price-move direction."""
    move_1m = float(row.get("1-min %", 0.0) or 0.0)
    move_5m = float(row.get("5-min %", 0.0) or 0.0)
    rank_change = row.get("Rank change")
    rank_jump = abs(int(rank_change)) if rank_change is not None else 0
    status = str(row.get("Status", ""))

    move_1m_score = min(abs(move_1m) / TOP10_SCORE_MAX_1M_PCT, 1.0) * 40
    move_5m_score = min(abs(move_5m) / TOP10_SCORE_MAX_5M_PCT, 1.0) * 30
    rank_score = min(rank_jump / TOP10_SCORE_MAX_RANK_JUMP, 1.0) * 20
    new_score = 10 if status == "NEW" else 0
    score = int(round(move_1m_score + move_5m_score + rank_score + new_score))

    if move_1m > 0 and move_5m > 0:
        direction = "UP"
    elif move_1m < 0 and move_5m < 0:
        direction = "DOWN"
    elif move_1m == 0 and move_5m == 0:
        direction = "NEUTRAL"
    else:
        direction = "MIXED"
    return min(score, 100), direction


def _add_signal_strength(annotated: pd.DataFrame) -> pd.DataFrame:
    """Add the transparent momentum score and direction to the live watchlist."""
    if annotated.empty:
        return annotated.copy()

    enriched = annotated.copy()
    signals = [_calculate_signal_strength(row) for row in enriched.to_dict("records")]
    enriched.insert(2, "Momentum score", [score for score, _ in signals])
    enriched.insert(3, "Direction", [direction for _, direction in signals])
    return enriched


def _add_signal_history(
    annotated: pd.DataFrame,
    history: list[pd.DataFrame] | None,
) -> pd.DataFrame:
    """Add previous-score, score-change, and signal-trend context from scan history."""
    if annotated.empty:
        return annotated.copy()

    enriched = annotated.copy()
    previous_scores: dict[tuple[str, str], int] = {}
    previous_directions: dict[tuple[str, str], str] = {}
    if history:
        previous = history[-1]
        if {"Exchange", "Symbol", "Momentum score", "Direction"}.issubset(previous.columns):
            for row in previous.to_dict("records"):
                key = (str(row["Exchange"]), str(row["Symbol"]))
                previous_scores[key] = int(row["Momentum score"])
                previous_directions[key] = str(row["Direction"])

    score_changes: list[int | None] = []
    score_trends: list[str] = []
    previous_values: list[int | None] = []
    direction_changes: list[str] = []
    for row in enriched.to_dict("records"):
        key = (str(row["Exchange"]), str(row["Symbol"]))
        score = int(row["Momentum score"])
        previous_score = previous_scores.get(key)
        previous_direction = previous_directions.get(key)
        previous_values.append(previous_score)
        if previous_score is None:
            score_changes.append(None)
            score_trends.append("NEW")
        else:
            change = score - previous_score
            score_changes.append(change)
            score_trends.append(
                "STRENGTHENING" if change > 0 else "WEAKENING" if change < 0 else "STABLE"
            )
        if previous_direction is None:
            direction_changes.append("NEW")
        elif previous_direction == row["Direction"]:
            direction_changes.append("UNCHANGED")
        else:
            direction_changes.append(f"{previous_direction}→{row['Direction']}")

    enriched.insert(
        4,
        "Previous score",
        pd.Series(previous_values, index=enriched.index, dtype=object),
    )
    enriched.insert(
        5,
        "Score change",
        pd.Series(score_changes, index=enriched.index, dtype=object),
    )
    enriched.insert(6, "Signal trend", score_trends)
    enriched.insert(7, "Direction change", direction_changes)
    return enriched


def _update_signal_history(
    history: list[pd.DataFrame] | None,
    annotated: pd.DataFrame,
    completed_at: datetime | None = None,
) -> list[pd.DataFrame]:
    """Append one completed scan to the rolling in-session signal history."""
    if annotated.empty:
        return list(history or [])

    snapshot_columns = [
        "Symbol",
        "Exchange",
        "Momentum score",
        "Direction",
    ]
    snapshot = annotated[
        [column for column in snapshot_columns if column in annotated.columns]
    ].copy()
    snapshot.insert(0, "Scan time", completed_at or datetime.now(_IST))
    updated = list(history or [])
    updated.append(snapshot.reset_index(drop=True))
    return updated[-TOP10_SIGNAL_HISTORY_LIMIT:]


def _should_record_signal_history(
    valid_quotes: int,
    partial_failures: int,
    data_age_seconds: float | None = None,
) -> bool:
    """Allow history updates only from complete, trusted, fresh provider scans."""
    return (
        valid_quotes >= TOP10_MIN_TRUSTED_COVERAGE_QUOTES
        and partial_failures == 0
        and data_age_seconds is not None
        and 0 <= data_age_seconds < TOP10_STALE_DATA_SECONDS
    )


def _signal_history_table(history: list[pd.DataFrame] | None) -> pd.DataFrame:
    """Flatten rolling signal snapshots into a compact analysis table."""
    if not history:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    for snapshot in history:
        for row in snapshot.to_dict("records"):
            rows.append(
                {
                    "Scan time": row.get("Scan time"),
                    "Symbol": row.get("Symbol"),
                    "Exchange": row.get("Exchange"),
                    "Momentum score": row.get("Momentum score"),
                    "Direction": row.get("Direction"),
                }
            )
    return pd.DataFrame(rows)


def _signal_history_trend(history: list[pd.DataFrame] | None) -> pd.DataFrame:
    """Return a timestamp-indexed score matrix for symbols seen in history."""
    table = _signal_history_table(history)
    if table.empty:
        return pd.DataFrame()

    table["Scan time"] = pd.to_datetime(table["Scan time"], errors="coerce")
    table = table.dropna(subset=["Scan time"])
    if table.empty:
        return pd.DataFrame()

    table["Label"] = table["Exchange"].astype(str) + ":" + table["Symbol"].astype(str)
    trend = table.pivot_table(
        index="Scan time",
        columns="Label",
        values="Momentum score",
        aggfunc="last",
    ).sort_index()
    return trend.tail(TOP10_SIGNAL_HISTORY_LIMIT)


def _signal_persistence(
    history: list[pd.DataFrame] | None,
) -> dict[tuple[str, str], tuple[int, str]]:
    """Calculate consecutive Top-10 presence and direction counts from history."""
    if not history:
        return {}

    latest_keys = {
        (str(row["Exchange"]), str(row["Symbol"])) for row in history[-1].to_dict("records")
    }
    persistence: dict[tuple[str, str], tuple[int, str]] = {}
    for key in latest_keys:
        count = 0
        direction_count = 0
        previous_direction: str | None = None
        for snapshot in reversed(history):
            rows = snapshot[
                (snapshot["Exchange"].astype(str) == key[0])
                & (snapshot["Symbol"].astype(str) == key[1])
            ]
            if rows.empty:
                break
            count += 1
            direction = str(rows.iloc[-1]["Direction"])
            if direction in {"UP", "DOWN"} and (
                previous_direction is None or direction == previous_direction
            ):
                direction_count += 1
                previous_direction = direction
            else:
                break
        persistence[key] = (count, previous_direction or "MIXED")
    return persistence


def _add_signal_persistence(
    annotated: pd.DataFrame,
    history: list[pd.DataFrame] | None,
) -> pd.DataFrame:
    """Add consecutive Top-10 scan persistence to the current watchlist."""
    if annotated.empty:
        return annotated.copy()

    persistence = _signal_persistence(history)
    counts: list[int] = []
    directions: list[str] = []
    for row in annotated.to_dict("records"):
        key = (str(row["Exchange"]), str(row["Symbol"]))
        count, direction = persistence.get(key, (0, "MIXED"))
        counts.append(count)
        directions.append(direction if count >= TOP10_PERSISTENCE_MIN_SCANS else "MIXED")

    enriched = annotated.copy()
    enriched["Persistence"] = counts
    enriched["Persistent direction"] = directions
    return enriched


def _persistence_alerts(annotated: pd.DataFrame) -> list[str]:
    """Build alerts for symbols that persist in the Top-10 across scans."""
    if annotated.empty or "Persistence" not in annotated.columns:
        return []

    alerts: list[str] = []
    for row in annotated.to_dict("records"):
        persistence = int(row.get("Persistence", 0) or 0)
        if persistence < TOP10_PERSISTENCE_ALERT_MIN_SCANS:
            continue
        symbol = f"{row['Exchange']}:{row['Symbol']}"
        direction = str(row.get("Persistent direction", "MIXED"))
        score = row.get("Momentum score")
        score_text = f" · score {int(score)}" if score is not None else ""
        if direction in {"UP", "DOWN"}:
            alerts.append(f"🔁 PERSISTENT {direction} · {symbol} · {persistence} scans{score_text}")
        else:
            alerts.append(f"🔁 PERSISTENT · {symbol} · {persistence} scans{score_text}")
    return alerts


def _signal_confirmation(row: dict[str, object]) -> str:
    """Classify Top-10 signal confirmation from momentum and persistence context."""
    score = int(row.get("Momentum score", 0) or 0)
    persistence = int(row.get("Persistence", 0) or 0)
    direction = str(row.get("Persistent direction", "MIXED"))
    signal_trend = str(row.get("Signal trend", "NEW"))

    if (
        score >= 60
        and persistence >= 3
        and direction in {"UP", "DOWN"}
        and signal_trend in {"STRENGTHENING", "STABLE"}
    ):
        return "CONFIRMED"
    if score >= 40 and persistence >= 2 and direction in {"UP", "DOWN"}:
        return "DEVELOPING"
    return "WEAK"


def _add_signal_confirmation(annotated: pd.DataFrame) -> pd.DataFrame:
    """Add a transparent confirmation state to the current Top-10 watchlist."""
    if annotated.empty:
        return annotated.copy()

    enriched = annotated.copy()
    enriched["Signal confirmation"] = [
        _signal_confirmation(row) for row in enriched.to_dict("records")
    ]
    return enriched


def _signal_quality_metrics(
    history: list[pd.DataFrame] | None,
) -> dict[str, float]:
    """Summarize descriptive quality metrics from completed Top-10 scans."""
    if not history:
        return {
            "Confirmation rate": 0.0,
            "Persistence rate": 0.0,
            "Direction consistency": 0.0,
            "Momentum consistency": 0.0,
        }

    rows = [row for snapshot in history for row in snapshot.to_dict("records")]
    if not rows:
        return {
            "Confirmation rate": 0.0,
            "Persistence rate": 0.0,
            "Direction consistency": 0.0,
            "Momentum consistency": 0.0,
        }

    total = len(rows)
    confirmed = sum(str(row.get("Signal confirmation", "")) == "CONFIRMED" for row in rows)
    persistent = sum(
        int(row.get("Persistence", 0) or 0) >= TOP10_PERSISTENCE_MIN_SCANS for row in rows
    )
    directional = sum(
        str(row.get("Persistent direction", "MIXED")) in {"UP", "DOWN"} for row in rows
    )
    strengthening = sum(
        str(row.get("Signal trend", "")) in {"STRENGTHENING", "STABLE"} for row in rows
    )
    return {
        "Confirmation rate": round(confirmed / total * 100, 1),
        "Persistence rate": round(persistent / total * 100, 1),
        "Direction consistency": round(directional / total * 100, 1),
        "Momentum consistency": round(strengthening / total * 100, 1),
    }


def _render_signal_quality_metrics(history: list[pd.DataFrame] | None) -> None:
    """Render descriptive signal-quality metrics for completed scans."""
    metrics = _signal_quality_metrics(history)
    st.caption("Descriptive statistics from completed Top-10 scans; not trade-performance results.")
    columns = st.columns(4)
    labels = (
        "Confirmation rate",
        "Persistence rate",
        "Direction consistency",
        "Momentum consistency",
    )
    for column, label in zip(columns, labels, strict=True):
        column.metric(label, f"{metrics[label]:.1f}%")


class Top10ScanError(RuntimeError):
    """Scan failure whose message is safe to show to the user."""


def _download_yahoo_frames(
    tickers: list[str],
    started: float,
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Fetch Yahoo candles, recovering unresolved symbols with strictly bounded stages.

    Every stage is capped (batch count, per-request timeout, no retry loops, a hard
    limit on single-symbol requests and an overall time budget) so a provider
    outage can never turn one scan into a retry storm.
    """
    frames, missing = download_symbol_frames(
        tickers,
        period="1d",
        interval="1m",
        auto_adjust=False,
        batch_size=TOP10_CHUNK_SIZE,
        timeout=TOP10_PROVIDER_TIMEOUT,
        retries=TOP10_PROVIDER_RETRIES,
        recover_missing=False,
        diagnostics=_PROVIDER_DIAGNOSTICS,
    )

    def budget_left() -> bool:
        return perf_counter() - started < TOP10_SCAN_BUDGET_SECONDS

    # Stage 2: ask again for only the unresolved symbols, in smaller batches. This
    # covers the case where a large batch returns no rows but smaller ones succeed.
    if missing and budget_left():
        recovered, missing = download_symbol_frames(
            missing,
            period="1d",
            interval="1m",
            auto_adjust=False,
            batch_size=TOP10_FALLBACK_CHUNK_SIZE,
            timeout=TOP10_FALLBACK_TIMEOUT,
            retries=0,
            recover_missing=False,
            diagnostics=_PROVIDER_DIAGNOSTICS,
        )
        frames = {**frames, **recovered}

    # Stage 3: direct per-symbol requests, only when a few symbols remain. A mass
    # failure is a provider-level problem that per-symbol requests would only amplify.
    if 0 < len(missing) <= TOP10_MAX_SINGLE_SYMBOL_RECOVERY and budget_left():
        recovered, missing = download_symbols_individually(
            missing,
            period="1d",
            interval="1m",
            auto_adjust=False,
            timeout=TOP10_FALLBACK_TIMEOUT,
            retries=0,
            max_symbols=TOP10_MAX_SINGLE_SYMBOL_RECOVERY,
            diagnostics=_PROVIDER_DIAGNOSTICS,
        )
        frames = {**frames, **recovered}

    if missing and not budget_left():
        _PROVIDER_DIAGNOSTICS.append(
            f"recovery stopped: scan time budget of {TOP10_SCAN_BUDGET_SECONDS}s reached"
        )
    return frames, missing


def _download_top10_frames(
    tickers: list[str],
) -> tuple[dict[str, pd.DataFrame], list[str], str]:
    """Prefer Dhan candles when configured, with bounded Yahoo recovery for gaps."""
    started = perf_counter()
    _PROVIDER_DIAGNOSTICS.clear()
    if dhan_provider_enabled():
        dhan_frames, dhan_missing = download_dhan_symbol_frames(tickers, interval=1)
        if dhan_missing:
            _PROVIDER_DIAGNOSTICS.append(
                f"Dhan returned no usable data for {len(dhan_missing)} symbol(s)"
            )
        if not dhan_missing:
            return dhan_frames, [], "Dhan"
        yahoo_frames, yahoo_missing = _download_yahoo_frames(dhan_missing, started)
        return {**dhan_frames, **yahoo_frames}, yahoo_missing, "Dhan + Yahoo fallback"
    frames, missing = _download_yahoo_frames(tickers, started)
    return frames, missing, "Yahoo"


def _describe_no_quotes(
    requested: int,
    missing: int,
    stale_ages: list[float],
    unusable: int,
) -> str:
    """Explain, in provider-neutral terms, why a scan produced zero usable quotes."""
    parts = [f"{missing} missing from the provider"]
    if stale_ages:
        parts.append(
            f"{len(stale_ages)} stale (freshest candle {min(stale_ages) / 60:.0f} min old)"
        )
    if unusable:
        parts.append(f"{unusable} with unusable candle data")
    return (
        f"No usable live quotes: 0 of {requested} symbols had a fresh 1-minute candle "
        f"({', '.join(parts)})."
    )


def _scan_live_top10() -> tuple[pd.DataFrame, float, int, int]:
    """Scan a small curated candidate set with one-minute candles only.

    Only real provider candles become rows: unresolved, stale or malformed symbols
    are skipped (and reported), never estimated or filled in.
    """
    started = perf_counter()
    rows: list[dict[str, object]] = []
    latest_candles: list[pd.Timestamp] = []

    candidates = [
        *(("NSE", symbol) for symbol in NSE_CANDIDATES[:TOP10_MAX_NSE_CANDIDATES]),
        *(("BSE", symbol) for symbol in BSE_CANDIDATES[:TOP10_MAX_BSE_CANDIDATES]),
    ]

    tickers_by_exchange = {
        exchange: [_ticker(symbol, exchange) for symbol in symbols]
        for exchange in ("NSE", "BSE")
        for symbols in [[symbol for venue, symbol in candidates if venue == exchange]]
    }
    all_tickers = [ticker for tickers in tickers_by_exchange.values() for ticker in tickers]
    frames, missing, provider_name = _download_top10_frames(all_tickers)
    failures = len(missing)

    scan_now = datetime.now(_IST)
    stale_ages: list[float] = []
    unusable = 0

    for exchange, tickers in tickers_by_exchange.items():
        for ticker in tickers:
            frame = frames.get(ticker)
            if frame is None or frame.empty or "Close" not in frame.columns:
                # Unresolved by the provider; already counted in ``failures``.
                continue
            close = pd.to_numeric(frame["Close"], errors="coerce").dropna()
            if len(close) < 2:
                unusable += 1
                continue

            candle_timestamp = close.index[-1]
            if not _is_fresh_provider_timestamp(candle_timestamp, scan_now):
                age = _provider_age_seconds(candle_timestamp, scan_now)
                if age is None:
                    unusable += 1
                else:
                    stale_ages.append(age)
                continue

            latest = float(close.iloc[-1])
            previous = float(close.iloc[-2])
            if latest <= 0 or previous <= 0:
                unusable += 1
                continue

            change_1m = (latest / previous - 1.0) * 100
            change_5m = (latest / float(close.iloc[-6]) - 1.0) * 100 if len(close) >= 6 else None
            latest_candles.append(pd.Timestamp(candle_timestamp))
            symbol = ticker.rsplit(".", 1)[0]

            rows.append(
                {
                    "Rank": 0,
                    "Symbol": symbol,
                    "Exchange": exchange,
                    "Price": round(latest, 2),
                    "1-min %": round(change_1m, 2),
                    "5-min %": round(change_5m, 2) if change_5m is not None else None,
                    "Last candle": _format_candle_time(close.index[-1]),
                }
            )

    if stale_ages:
        _PROVIDER_DIAGNOSTICS.append(
            f"{len(stale_ages)} symbol(s) skipped: latest candle older than "
            f"{TOP10_STALE_DATA_SECONDS}s (freshest {min(stale_ages):.0f}s old)"
        )
    if unusable:
        _PROVIDER_DIAGNOSTICS.append(
            f"{unusable} symbol(s) skipped: insufficient or invalid candle data"
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        message = _describe_no_quotes(len(all_tickers), failures, stale_ages, unusable)
        _PROVIDER_DIAGNOSTICS.append(message)
        raise Top10ScanError(message)

    valid_quotes = len(frame)
    trusted_quotes = min(valid_quotes, TOP10_EXPECTED_QUOTES)
    frame.attrs["provider"] = provider_name
    frame.attrs["expected_quotes"] = TOP10_EXPECTED_QUOTES
    frame.attrs["candidate_pool_size"] = len(all_tickers)
    frame.attrs["coverage_complete"] = trusted_quotes >= TOP10_EXPECTED_QUOTES
    frame.attrs["latest_candle_at"] = max(latest_candles) if latest_candles else None
    frame = (
        frame.assign(_abs_change=frame["1-min %"].abs())
        .sort_values("_abs_change", ascending=False)
        .head(10)
        .drop(columns="_abs_change")
        .reset_index(drop=True)
    )
    frame["Rank"] = range(1, len(frame) + 1)
    return frame, round(perf_counter() - started, 2), failures, trusted_quotes


@st.cache_data(ttl=TOP10_CACHE_SECONDS, show_spinner=False)
def _load_live_top10() -> tuple[pd.DataFrame, float, int, int]:
    """Cached fallback for the live Top-10 scan."""
    return _scan_live_top10()


@dataclass(frozen=True)
class _ScanSnapshot:
    """Consistent, lock-free view of the shared background scan state."""

    result: tuple[pd.DataFrame, float, int, int] | None
    generation: int
    completed_at: datetime | None
    failures: int
    last_error: str | None
    running: bool
    next_attempt_at: datetime | None
    diagnostics: tuple[str, ...]


def _retry_delay_seconds(failures: int) -> int:
    """Exponential retry backoff after consecutive failed scans, capped per minute."""
    if failures <= 0:
        return 0
    return min(
        TOP10_RETRY_BACKOFF_SECONDS * 2 ** (failures - 1),
        TOP10_RETRY_BACKOFF_MAX_SECONDS,
    )


def _safe_error_message(exc: BaseException) -> str:
    """Return a user-safe failure summary; raw provider errors stay in the server log."""
    if isinstance(exc, Top10ScanError):
        return str(exc)
    return f"Quote provider error ({type(exc).__name__})."


def _reset_scan_state() -> None:
    """Forget all shared scan state (used by tests; the executor is left alone)."""
    global _SCAN_FUTURE, _SCAN_RESULT, _SCAN_FAILURES, _SCAN_COMPLETED_AT
    global _SCAN_GENERATION, _SCAN_LAST_ERROR, _SCAN_NEXT_ATTEMPT_AT, _SCAN_STARTED_AT
    global _SCAN_FINISHED_AT
    with _SCAN_LOCK:
        _SCAN_FUTURE = None
        _SCAN_RESULT = None
        _SCAN_FAILURES = 0
        _SCAN_COMPLETED_AT = None
        _SCAN_GENERATION = 0
        _SCAN_LAST_ERROR = None
        _SCAN_NEXT_ATTEMPT_AT = None
        _SCAN_STARTED_AT = None
        _SCAN_FINISHED_AT = None
        _LAST_SCAN_DIAGNOSTICS.clear()
        _PROVIDER_DIAGNOSTICS.clear()


def _run_background_scan(token: int) -> tuple[pd.DataFrame, float, int, int]:
    """Worker entry point: run one scan; publish its diagnostics and finish time."""
    global _SCAN_FINISHED_AT
    try:
        return _scan_live_top10()
    finally:
        with _SCAN_LOCK:
            # A scan abandoned by the watchdog must not overwrite newer state.
            if token == _SCAN_TOKEN:
                _LAST_SCAN_DIAGNOSTICS[:] = list(dict.fromkeys(_PROVIDER_DIAGNOSTICS))
                _SCAN_FINISHED_AT = datetime.now(_IST)


def _record_scan_failure(message: str, now: datetime) -> None:
    """Register one failed scan and schedule the next attempt. Caller holds the lock."""
    global _SCAN_FAILURES, _SCAN_LAST_ERROR, _SCAN_NEXT_ATTEMPT_AT
    _SCAN_FAILURES += 1
    _SCAN_LAST_ERROR = message
    _SCAN_NEXT_ATTEMPT_AT = now + timedelta(seconds=_retry_delay_seconds(_SCAN_FAILURES))


def _settle_background_scan(now: datetime) -> None:
    """Fold a finished (or stuck) background scan into the shared state.

    The last successful result is never discarded by a failed refresh. Caller must
    hold ``_SCAN_LOCK``.
    """
    global _SCAN_FUTURE, _SCAN_RESULT, _SCAN_FAILURES, _SCAN_COMPLETED_AT
    global _SCAN_GENERATION, _SCAN_LAST_ERROR, _SCAN_NEXT_ATTEMPT_AT
    global _SCAN_EXECUTOR, _SCAN_TOKEN
    if _SCAN_FUTURE is None:
        return

    if not _SCAN_FUTURE.done():
        started = _SCAN_STARTED_AT
        if started is None or now - started < timedelta(seconds=TOP10_SCAN_HARD_TIMEOUT_SECONDS):
            return
        # A hung provider call must not leave the page refreshing forever: orphan the
        # stuck worker (its late result is ignored) and move to a fresh executor.
        _SCAN_TOKEN += 1
        _SCAN_FUTURE = None
        _SCAN_EXECUTOR.shutdown(wait=False, cancel_futures=True)
        _SCAN_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="top10-scan")
        message = f"Live scan timed out after {TOP10_SCAN_HARD_TIMEOUT_SECONDS}s."
        _LAST_SCAN_DIAGNOSTICS[:] = [message]
        _record_scan_failure(message, now)
        logger.warning("Top-10 scan abandoned: %s", message)
        return

    future, _SCAN_FUTURE = _SCAN_FUTURE, None
    finished = _SCAN_FINISHED_AT or now
    try:
        result = future.result()
    except Exception as exc:  # provider failures must never crash the page
        logger.warning("Top-10 scan failed (%s)", type(exc).__name__, exc_info=exc)
        _record_scan_failure(_safe_error_message(exc), finished)
    else:
        _SCAN_RESULT = result
        _SCAN_COMPLETED_AT = finished
        _SCAN_GENERATION += 1
        _SCAN_FAILURES = 0
        _SCAN_LAST_ERROR = None
        _SCAN_NEXT_ATTEMPT_AT = finished + timedelta(seconds=TOP10_REFRESH_SECONDS)


def _scan_snapshot(now: datetime | None = None) -> _ScanSnapshot:
    """Settle any finished scan, then return the current shared scan state."""
    current = now or datetime.now(_IST)
    with _SCAN_LOCK:
        _settle_background_scan(current)
        return _ScanSnapshot(
            result=_SCAN_RESULT,
            generation=_SCAN_GENERATION,
            completed_at=_SCAN_COMPLETED_AT,
            failures=_SCAN_FAILURES,
            last_error=_SCAN_LAST_ERROR,
            running=_SCAN_FUTURE is not None,
            next_attempt_at=_SCAN_NEXT_ATTEMPT_AT,
            diagnostics=tuple(_LAST_SCAN_DIAGNOSTICS),
        )


def _start_background_scan(*, now: datetime | None = None, force: bool = False) -> bool:
    """Start one shared scan without blocking the Streamlit fragment.

    Returns True only when a scan was actually started. At most one scan runs at a
    time. Automatic starts wait out the retry backoff after a failure; ``force``
    (the manual button) bypasses the backoff but is still rate limited.
    """
    global _SCAN_FUTURE, _SCAN_STARTED_AT, _SCAN_FINISHED_AT, _SCAN_TOKEN
    current = now or datetime.now(_IST)
    with _SCAN_LOCK:
        _settle_background_scan(current)
        if _SCAN_FUTURE is not None:
            return False
        if force:
            if _SCAN_STARTED_AT is not None and current < _SCAN_STARTED_AT + timedelta(
                seconds=TOP10_MANUAL_REFRESH_MIN_SECONDS
            ):
                return False
        elif _SCAN_NEXT_ATTEMPT_AT is not None and current < _SCAN_NEXT_ATTEMPT_AT:
            return False
        _SCAN_TOKEN += 1
        _SCAN_STARTED_AT = current
        _SCAN_FINISHED_AT = None
        _SCAN_FUTURE = _SCAN_EXECUTOR.submit(_run_background_scan, _SCAN_TOKEN)
        return True


def _sync_session_with_snapshot(snapshot: _ScanSnapshot) -> None:
    """Copy a newly completed shared scan into this session's state exactly once."""
    if snapshot.result is None:
        return
    if snapshot.generation == st.session_state.get(TOP10_SEEN_GENERATION_KEY):
        return
    st.session_state["top10_live_previous_result"] = st.session_state.get(
        "top10_live_result", (pd.DataFrame(), 0.0, 0, 0)
    )[0]
    st.session_state["top10_live_result"] = snapshot.result
    st.session_state["top10_live_completed_at"] = snapshot.completed_at
    st.session_state[TOP10_PARTIAL_FAILURES_KEY] = snapshot.result[2]
    st.session_state[TOP10_COVERAGE_KEY] = snapshot.result[3]
    st.session_state[TOP10_SEEN_GENERATION_KEY] = snapshot.generation


def _render_provider_diagnostics(diagnostics: tuple[str, ...]) -> None:
    """Show the safe diagnostic summary of the last completed scan, if any."""
    if diagnostics:
        st.caption("Provider diagnostics (safe summary): " + "; ".join(dict.fromkeys(diagnostics)))


def _handle_manual_refresh() -> None:
    """Handle the manual refresh button: market-hours gated and rate limited."""
    now = datetime.now(_IST)
    if not _market_is_open(now):
        st.info(
            "⚪ MARKET CLOSED · Live Top-10 refresh is available during the next "
            "regular NSE/BSE session."
        )
        return
    _load_live_top10.clear()
    _start_background_scan(now=now, force=True)


def _render_live_top10_results() -> None:
    """Render the auto-refreshing results area. It contains no widgets."""
    now = datetime.now(_IST)
    market_open = _market_is_open(now)

    snapshot = _scan_snapshot(now)
    _sync_session_with_snapshot(snapshot)

    top10, scan_seconds, partial_failures, valid_quotes = st.session_state.get(
        "top10_live_result",
        (pd.DataFrame(), 0.0, 0, 0),
    )
    completed_at = st.session_state.get("top10_live_completed_at")
    scan_running = snapshot.running

    refresh_due = market_open and (
        completed_at is None or now >= completed_at + timedelta(seconds=TOP10_REFRESH_SECONDS)
    )
    if not scan_running and refresh_due and _start_background_scan(now=now):
        scan_running = True
    next_refresh = snapshot.next_attempt_at or (now + timedelta(seconds=TOP10_REFRESH_SECONDS))
    scan_failed = snapshot.failures > 0 and snapshot.last_error is not None and not scan_running

    if not market_open:
        session_status = "MARKET_CLOSED"
    elif scan_running:
        session_status = "REFRESHING"
    elif scan_failed:
        session_status = "PROVIDER_ERROR"
    else:
        session_status = "READY"

    st.session_state[TOP10_SESSION_STATUS_KEY] = session_status

    if top10.empty:
        # Exactly one status message while there is nothing to show.
        if not market_open:
            st.info(
                "⚪ MARKET CLOSED · No live Top-10 scan is available outside market hours. "
                "Live scanning will begin during the next regular NSE/BSE session."
            )
        elif scan_running:
            st.info("🟡 REFRESHING · Fetching the first live Top-10 scan in the background…")
        elif scan_failed and snapshot.failures >= TOP10_MAX_CONSECUTIVE_FAILURES:
            st.error(
                f"🔴 LIVE DATA UNAVAILABLE · {snapshot.last_error} "
                f"Retrying automatically at {next_refresh:%H:%M:%S} IST."
            )
        elif scan_failed:
            st.warning(
                f"🟠 SCAN FAILED · {snapshot.last_error} "
                f"Retrying automatically at {next_refresh:%H:%M:%S} IST."
            )
        else:
            st.info("🟡 REFRESHING · Waiting for the first live Top-10 scan to start…")
        _render_provider_diagnostics(snapshot.diagnostics)
        return

    if not market_open:
        st.info(
            "⚪ MARKET CLOSED · Showing the last completed scan. Live scanning resumes "
            "during the next regular NSE/BSE session."
        )
    if scan_failed:
        st.warning(
            "🟠 PROVIDER ISSUE · Showing the last successful Top-10"
            f" from {completed_at:%H:%M:%S} IST. {snapshot.last_error} "
            f"Automatic retry at {next_refresh:%H:%M:%S} IST."
        )
    elif partial_failures:
        unresolved = max(0, TOP10_EXPECTED_QUOTES - valid_quotes)
        st.warning(
            f"🟠 PARTIAL PROVIDER ISSUE · {unresolved} quote(s) remain unresolved after retries. "
            "Displayed results may be incomplete; automatic retry is active. "
            "Do not use these rows for trading decisions."
        )

    _render_provider_diagnostics(snapshot.diagnostics)
    st.caption(f"Quote provider: {top10.attrs.get('provider', 'unknown')}")

    scan_age_seconds = (
        max(0.0, (now - completed_at).total_seconds()) if completed_at is not None else None
    )
    provider_age_seconds = _provider_age_seconds(top10.attrs.get("latest_candle_at"), now)
    data_age_seconds = (
        provider_age_seconds if provider_age_seconds is not None else scan_age_seconds
    )
    if scan_running:
        status = "🟡 REFRESHING · showing previous data"
    elif scan_failed:
        status = "🟠 REFRESH FAILED · showing last successful scan"
    elif data_age_seconds is not None and data_age_seconds >= TOP10_STALE_DATA_SECONDS:
        status = "🔴 STALE DATA · latest completed data"
    elif completed_at is not None and scan_seconds >= TOP10_SCAN_WARNING_SECONDS:
        status = "🟠 SLOW SCAN · latest completed data"
    elif completed_at is not None:
        status = "🟢 FRESH · latest completed scan"
    else:
        status = "⚪ PREVIOUS DATA"

    last_update = completed_at.strftime("%H:%M:%S") if completed_at is not None else "—"
    coverage_status = _coverage_status(valid_quotes)
    previous_top10 = st.session_state.get("top10_live_previous_result")
    annotated_top10, dropped_symbols = _annotate_watchlist_changes(top10, previous_top10)
    annotated_top10 = _add_signal_strength(annotated_top10)
    signal_history = st.session_state.get(TOP10_SIGNAL_HISTORY_KEY, [])
    annotated_top10 = _add_signal_history(annotated_top10, signal_history)
    annotated_top10 = _add_signal_persistence(annotated_top10, signal_history)
    annotated_top10 = _add_signal_confirmation(annotated_top10)
    data_is_fresh = (
        data_age_seconds is not None and 0 <= data_age_seconds < TOP10_STALE_DATA_SECONDS
    )
    change_alerts = _watchlist_change_alerts(annotated_top10) if data_is_fresh else []
    persistence_alerts = _persistence_alerts(annotated_top10) if data_is_fresh else []
    if not data_is_fresh:
        st.warning(
            "Signals are informational only: provider data is stale or its age cannot be verified. "
            "Refresh data before considering any decision."
        )
    if completed_at != st.session_state.get(
        TOP10_SIGNAL_HISTORY_UPDATED_KEY
    ) and _should_record_signal_history(valid_quotes, partial_failures, data_age_seconds):
        signal_history = _update_signal_history(signal_history, annotated_top10, completed_at)
        st.session_state[TOP10_SIGNAL_HISTORY_KEY] = signal_history
        st.session_state[TOP10_SIGNAL_HISTORY_UPDATED_KEY] = completed_at
    st.caption(
        f"{status} · Last update {last_update} IST · "
        f"Next refresh {next_refresh:%H:%M:%S} IST · "
        f"Provider data age {data_age_seconds:.0f}s · Scan {scan_seconds:.1f}s · "
        f"Provider failures {partial_failures} · Quotes {valid_quotes}/{TOP10_EXPECTED_QUOTES} · "
        f"Coverage {coverage_status} · Refresh every 60s"
    )
    if dropped_symbols:
        st.caption(f"🔵 DROPPED SINCE LAST SCAN · {', '.join(dropped_symbols)}")
    if change_alerts:
        st.warning(" · ".join(change_alerts[:5]))
    if persistence_alerts:
        st.info(" · ".join(persistence_alerts[:5]))
    _render_signal_quality_metrics(signal_history)

    if coverage_status == "CRITICAL":
        st.error(
            f"🔴 CRITICAL QUOTE COVERAGE · Only {valid_quotes}/{TOP10_EXPECTED_QUOTES} "
            "quotes are valid. Displayed Top-10 data may be materially incomplete; "
            "automatic retry is active."
        )
    elif coverage_status == "REDUCED":
        st.warning(
            f"🟠 REDUCED QUOTE COVERAGE · {valid_quotes}/{TOP10_EXPECTED_QUOTES} quotes are valid. "
            "Displayed results may be incomplete; automatic retry is active."
        )

    st.dataframe(
        annotated_top10,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Rank": st.column_config.NumberColumn("Rank", width="small"),
            "Rank change": st.column_config.NumberColumn("Rank change", width="small"),
            "Momentum score": st.column_config.NumberColumn("Momentum score", width="small"),
            "Direction": st.column_config.TextColumn("Direction", width="small"),
            "Previous score": st.column_config.NumberColumn("Previous score", width="small"),
            "Score change": st.column_config.NumberColumn("Score change", width="small"),
            "Signal trend": st.column_config.TextColumn("Signal trend", width="small"),
            "Direction change": st.column_config.TextColumn("Direction change", width="small"),
            "Persistence": st.column_config.NumberColumn("Persistence", width="small"),
            "Persistent direction": st.column_config.TextColumn(
                "Persistent direction", width="small"
            ),
            "Signal confirmation": st.column_config.TextColumn(
                "Signal confirmation", width="small"
            ),
            "Price": st.column_config.NumberColumn("Price", format="₹%.2f"),
            "1-min %": st.column_config.NumberColumn("1-min %", format="%.2f"),
            "5-min %": st.column_config.NumberColumn("5-min %", format="%.2f"),
        },
    )

    history_table = _signal_history_table(signal_history)
    history_trend = _signal_history_trend(signal_history)
    if not history_table.empty:
        with st.expander("📈 Top-10 Signal History", expanded=False):
            st.caption(
                f"Rolling history of the last {len(signal_history)} completed scans. "
                "Scores are scanner signals, not trade recommendations."
            )
            st.dataframe(
                history_table.sort_values("Scan time", ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Scan time": st.column_config.DatetimeColumn(
                        "Scan time",
                        format="HH:mm:ss",
                    ),
                    "Momentum score": st.column_config.NumberColumn(
                        "Momentum score",
                        min_value=0,
                        max_value=100,
                    ),
                },
            )
            if not history_trend.empty:
                st.line_chart(history_trend)


@st.fragment(run_every=f"{TOP10_UI_POLL_SECONDS}s")
def _live_top10_fragment() -> None:
    """Poll the shared scan state, replacing a single output slot on every run.

    Only non-widget elements live in this auto-refreshing fragment, and they are
    written into one ``st.empty()`` slot so a poll can never stack a second copy of
    the status messages or the table on top of the previous one.
    """
    with st.empty().container():
        _render_live_top10_results()


def show_live_top10_scanner(*, period: str = "6mo", interval: str = "1d") -> None:
    """Render the live Top-10 scanner: static controls once, results auto-refreshing."""
    del period, interval

    st.subheader("🔴 Live Top-10 Market Scanner")
    st.caption(
        "Ranks the largest absolute 1-minute price moves from the configured "
        "NSE/BSE candidate universe. Dhan is preferred when configured; Yahoo Finance is the fallback. The fast path scans a balanced sample of NSE and BSE symbols. "
        "Degraded coverage is never promoted into signal history."
    )

    if st.button("↻ Refresh Top-10 now", key="top10_manual_refresh"):
        _handle_manual_refresh()

    _live_top10_fragment()
