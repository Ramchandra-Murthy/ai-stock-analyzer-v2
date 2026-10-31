"""Fast live Top-10 market-mover scanner with one-minute refresh."""

# The fast path scans a balanced, bounded NSE/BSE pool to keep live refresh latency bounded.

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Lock
from time import perf_counter
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES
from services.dhan_live_provider import dhan_provider_enabled, download_dhan_symbol_frames
from services.resilient_market_data import download_symbol_frames
from services.symbol_resolver import yahoo_ticker

TOP10_REFRESH_SECONDS = 60
TOP10_UI_POLL_SECONDS = 2
TOP10_CACHE_SECONDS = 50
TOP10_TIMEZONE = "Asia/Kolkata"
TOP10_CHUNK_SIZE = 20
TOP10_MAX_NSE_CANDIDATES = 10
TOP10_MAX_BSE_CANDIDATES = 10
TOP10_PROVIDER_RETRIES = 0
TOP10_PROVIDER_TIMEOUT = 5
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
_SCAN_RESULT: tuple[pd.DataFrame, float, int, int] | None = None
_SCAN_FAILURES = 0
_PROVIDER_DIAGNOSTICS: list[str] = []


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
    return yahoo_ticker(cleaned if cleaned.endswith((".NS", ".BO")) else f"{cleaned}{suffix}")


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


def _download_top10_frames(
    tickers: list[str],
) -> tuple[dict[str, pd.DataFrame], list[str], str]:
    """Prefer Dhan candles when configured, with Yahoo fallback for gaps."""
    global _PROVIDER_DIAGNOSTICS
    _PROVIDER_DIAGNOSTICS = []
    if dhan_provider_enabled():
        dhan_frames, dhan_missing = download_dhan_symbol_frames(tickers, interval=1)
        if dhan_missing:
            _PROVIDER_DIAGNOSTICS.append(
                f"Dhan returned no usable data for {len(dhan_missing)} symbol(s)"
            )
        if not dhan_missing:
            return dhan_frames, [], "Dhan"
        yahoo_frames, yahoo_missing = download_symbol_frames(
            dhan_missing,
            period="1d",
            interval="1m",
            auto_adjust=False,
            batch_size=TOP10_CHUNK_SIZE,
            timeout=TOP10_PROVIDER_TIMEOUT,
            retries=TOP10_PROVIDER_RETRIES,
            recover_missing=False,
            diagnostics=_PROVIDER_DIAGNOSTICS,
        )
        merged = {**dhan_frames, **yahoo_frames}
        return merged, yahoo_missing, "Dhan + Yahoo fallback"
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
    return frames, missing, "Yahoo"


def _scan_live_top10() -> tuple[pd.DataFrame, float, int, int]:
    """Scan a small curated candidate set with one-minute candles only."""
    started = perf_counter()
    failures = 0
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
    frames, _missing, provider_name = _download_top10_frames(all_tickers)
    failures = len(_missing) if _missing else 0

    for exchange, tickers in tickers_by_exchange.items():
        for ticker in tickers:
            close = pd.to_numeric(
                frames.get(ticker, pd.DataFrame()).get("Close"),
                errors="coerce",
            ).dropna()
            if len(close) < 2:
                continue

            candle_timestamp = close.index[-1]
            if not _is_fresh_provider_timestamp(candle_timestamp, datetime.now(_IST)):
                continue

            latest = float(close.iloc[-1])
            previous = float(close.iloc[-2])
            if latest <= 0 or previous <= 0:
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

    frame = pd.DataFrame(rows)
    if frame.empty:
        raise RuntimeError("Live quote provider returned no usable 1-minute quotes")
    if frame.empty:
        return frame, round(perf_counter() - started, 2), failures, 0

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


def _start_background_scan() -> None:
    """Start one shared scan without blocking the Streamlit fragment."""
    global _SCAN_FUTURE
    with _SCAN_LOCK:
        if _SCAN_FUTURE is None or _SCAN_FUTURE.done():
            _SCAN_FUTURE = _SCAN_EXECUTOR.submit(_scan_live_top10)


def _consume_background_scan() -> tuple[pd.DataFrame, float, int, int] | None:
    """Return a completed background scan and keep the UI non-blocking."""
    global _SCAN_FUTURE, _SCAN_RESULT, _SCAN_FAILURES
    with _SCAN_LOCK:
        if _SCAN_FUTURE is not None and _SCAN_FUTURE.done():
            try:
                _SCAN_RESULT = _SCAN_FUTURE.result()
            except Exception:
                _SCAN_RESULT = None
                _SCAN_FAILURES += 1
            else:
                _SCAN_FAILURES = 0
            _SCAN_FUTURE = None
        return _SCAN_RESULT


@st.fragment(run_every=f"{TOP10_UI_POLL_SECONDS}s")
def show_live_top10_scanner(*, period: str = "6mo", interval: str = "1d") -> None:
    """Render a live Top-10 scanner while refresh work runs in the background."""
    del period, interval

    st.subheader("🔴 Live Top-10 Market Scanner")
    st.caption(
        "Ranks the largest absolute 1-minute price moves from the configured "
        "NSE/BSE candidate universe. Dhan is preferred when configured; Yahoo Finance is the fallback. The fast path scans a balanced sample of NSE and BSE symbols. "
        "Degraded coverage is never promoted into signal history."
    )

    if st.button("↻ Refresh Top-10 now", key="top10_manual_refresh"):
        if _market_is_open(datetime.now(_IST)):
            _load_live_top10.clear()
            _start_background_scan()
            st.rerun(scope="fragment")
        else:
            st.info(
                "⚪ MARKET CLOSED · Live Top-10 refresh is available during the next "
                "regular NSE/BSE session."
            )

    background_result = _consume_background_scan()
    if background_result is not None:
        st.session_state["top10_live_previous_result"] = st.session_state.get(
            "top10_live_result", (pd.DataFrame(), 0.0, 0, 0)
        )[0]
        st.session_state["top10_live_result"] = background_result
        st.session_state["top10_live_completed_at"] = datetime.now(_IST)
        st.session_state[TOP10_PARTIAL_FAILURES_KEY] = background_result[2]
        st.session_state[TOP10_COVERAGE_KEY] = background_result[3]

    top10, scan_seconds, partial_failures, valid_quotes = st.session_state.get(
        "top10_live_result",
        (pd.DataFrame(), 0.0, 0, 0),
    )
    completed_at = st.session_state.get("top10_live_completed_at")
    scan_running = _SCAN_FUTURE is not None and not _SCAN_FUTURE.done()

    now = datetime.now(_IST)
    market_open = _market_is_open(now)

    refresh_due = market_open and (
        completed_at is None or now >= completed_at + timedelta(seconds=TOP10_REFRESH_SECONDS)
    )
    if not scan_running and refresh_due:
        _start_background_scan()
        scan_running = True
    next_refresh = (
        (completed_at + timedelta(seconds=TOP10_REFRESH_SECONDS))
        if completed_at is not None
        else now + timedelta(seconds=TOP10_REFRESH_SECONDS)
    )

    if not market_open:
        session_status = "MARKET_CLOSED"
        st.info("⚪ MARKET CLOSED · Live scanning resumes during the next regular NSE/BSE session.")
    elif scan_running:
        session_status = "REFRESHING"
        st.info("🟡 LIVE REFRESH · Updating the Top-10 in the background.")
    else:
        session_status = "READY"

    st.session_state[TOP10_SESSION_STATUS_KEY] = session_status

    if top10.empty:
        if not market_open:
            st.info(
                "⚪ MARKET CLOSED · No live Top-10 scan is available outside market hours. "
                "Live scanning will begin during the next regular NSE/BSE session."
            )
        elif _SCAN_FAILURES >= TOP10_MAX_CONSECUTIVE_FAILURES:
            st.error(
                "🔴 LIVE DATA UNAVAILABLE · The quote provider failed repeatedly. "
                "Retrying automatically."
            )
        else:
            st.info("🟡 REFRESHING · Fetching the first live Top-10 scan in the background…")
        if _PROVIDER_DIAGNOSTICS:
            st.caption(
                "Provider diagnostics (safe summary): "
                + "; ".join(dict.fromkeys(_PROVIDER_DIAGNOSTICS))
            )
        return

    if _SCAN_FAILURES >= TOP10_MAX_CONSECUTIVE_FAILURES:
        st.warning(
            "🟠 PROVIDER ISSUE · Showing the last successful Top-10. Automatic retry is active."
        )
    elif partial_failures:
        unresolved = max(0, TOP10_EXPECTED_QUOTES - valid_quotes)
        st.warning(
            f"🟠 PARTIAL PROVIDER ISSUE · {unresolved} quote(s) remain unresolved after retries. "
            "Displayed results may be incomplete; automatic retry is active. "
            "Do not use these rows for trading decisions."
        )

    if _PROVIDER_DIAGNOSTICS:
        st.caption(
            "Provider diagnostics (safe summary): "
            + "; ".join(dict.fromkeys(_PROVIDER_DIAGNOSTICS))
        )
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
