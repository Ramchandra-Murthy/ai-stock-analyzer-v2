"""Durable persistence for timestamped AI signal records and outcomes.

Supabase is preferred when server-side credentials are configured. SQLite is
used for local development and deployments with a durable mounted volume.
A container's ephemeral filesystem is not durable across redeployments.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from contextlib import closing
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ai_trading.signal_history import SignalRecord, attach_outcomes

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_PATH = Path("data/ai_signal_history.sqlite3")
SUPABASE_TABLE = "ai_signal_history"


class SignalHistoryStoreError(RuntimeError):
    """Raised when signal history cannot be persisted or loaded."""


def _supabase_credentials() -> tuple[str, str] | None:
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = (
        os.environ.get("SUPABASE_SECRET_KEY", "").strip()
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    )
    try:
        import streamlit as st

        if not url:
            url = str(st.secrets.get("SUPABASE_URL", "")).strip().rstrip("/")
        if not key:
            key = str(
                st.secrets.get("SUPABASE_SECRET_KEY", "")
                or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
            ).strip()
    except Exception as exc:
        logger.debug("Streamlit secrets unavailable for signal history: %s", exc)
    return (url, key) if url and key else None


def signal_history_backend() -> str:
    """Return the configured backend name without exposing credentials."""
    return "supabase" if _supabase_credentials() else "sqlite"


def _supabase_request(
    method: str,
    query: str = "",
    payload: list[dict[str, Any]] | None = None,
    *,
    prefer: str | None = None,
) -> list[dict[str, Any]]:
    credentials = _supabase_credentials()
    if credentials is None:
        raise SignalHistoryStoreError("Supabase credentials are not configured.")
    base_url, secret = credentials
    url = f"{base_url}/rest/v1/{SUPABASE_TABLE}"
    if query:
        url = f"{url}?{query}"
    body = None if payload is None else json.dumps(payload, default=str).encode("utf-8")
    headers = {
        "apikey": secret,
        "Authorization": f"Bearer {secret}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            content = response.read().decode("utf-8")
            if not content:
                return []
            decoded = json.loads(content)
            return decoded if isinstance(decoded, list) else []
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise SignalHistoryStoreError(
            f"Supabase signal-history request failed (HTTP {exc.code}). "
            "Verify the ai_signal_history migration and server-side key. "
            + (detail if exc.code < 500 else "Database service is temporarily unavailable.")
        ) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SignalHistoryStoreError(
            "Could not reach Supabase while accessing AI signal history."
        ) from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise SignalHistoryStoreError(
            "Supabase returned an unreadable signal-history response."
        ) from exc


def _database_path() -> Path:
    return Path(os.environ.get("AI_SIGNAL_HISTORY_DATABASE_PATH", str(DEFAULT_DATABASE_PATH)))


def _connect() -> sqlite3.Connection:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("""
        CREATE TABLE IF NOT EXISTS ai_signal_history (
            signal_timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            exchange TEXT NOT NULL,
            record_json TEXT NOT NULL,
            outcome_json TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (signal_timestamp, symbol, exchange)
        )
        """)
    return connection


def _timestamp_key(value: Any) -> str:
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        raise SignalHistoryStoreError("Signal timestamp is missing or invalid.")
    return timestamp.isoformat()


def _json_safe(value: Any) -> Any:
    if value is None or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and pd.isna(value):
        return None
    return value


def _record_payload(record: SignalRecord) -> dict[str, Any]:
    payload = asdict(record)
    payload["timestamp"] = record.timestamp.isoformat()
    return payload


def _record_from_payload(payload: dict[str, Any]) -> SignalRecord:
    values = dict(payload)
    values["timestamp"] = datetime.fromisoformat(str(values["timestamp"]))
    return SignalRecord(**values)


def save_signal_snapshot(
    records: list[SignalRecord],
    history: pd.DataFrame | None = None,
) -> int:
    """Upsert signal inputs and their latest computed outcomes idempotently."""
    if not records:
        return 0
    outcomes: dict[tuple[str, str, str], dict[str, Any]] = {}
    if isinstance(history, pd.DataFrame) and not history.empty:
        for row in history.to_dict("records"):
            key = (
                _timestamp_key(row.get("timestamp")),
                str(row.get("symbol", "")).upper(),
                str(row.get("exchange", "")).upper(),
            )
            outcomes[key] = {name: _json_safe(value) for name, value in row.items()}

    payload = []
    for record in records:
        timestamp = _timestamp_key(record.timestamp)
        key = (timestamp, record.symbol.upper(), record.exchange.upper())
        payload.append(
            {
                "signal_timestamp": timestamp,
                "symbol": record.symbol.upper(),
                "exchange": record.exchange.upper(),
                "record": _record_payload(record),
                "outcome": outcomes.get(key),
            }
        )

    if _supabase_credentials():
        query = urllib.parse.urlencode(
            {"on_conflict": "signal_timestamp,symbol,exchange"},
            safe=",",
        )
        supabase_payload = [
            {key: value for key, value in item.items() if key != "outcome" or value is not None}
            for item in payload
        ]
        _supabase_request(
            "POST",
            query,
            supabase_payload,
            prefer="resolution=merge-duplicates,return=minimal",
        )
    else:
        try:
            with closing(_connect()) as connection, connection:
                connection.executemany(
                    """
                    INSERT INTO ai_signal_history (
                        signal_timestamp, symbol, exchange, record_json, outcome_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(signal_timestamp, symbol, exchange) DO UPDATE SET
                        record_json = excluded.record_json,
                        outcome_json = COALESCE(excluded.outcome_json, ai_signal_history.outcome_json),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    [
                        (
                            item["signal_timestamp"],
                            item["symbol"],
                            item["exchange"],
                            json.dumps(item["record"], default=str),
                            (
                                json.dumps(item["outcome"], default=str)
                                if item["outcome"] is not None
                                else None
                            ),
                        )
                        for item in payload
                    ],
                )
        except sqlite3.Error as exc:
            raise SignalHistoryStoreError("Could not save AI signal history to SQLite.") from exc
    return len(payload)


def load_signal_snapshot() -> tuple[list[SignalRecord], pd.DataFrame]:
    """Load persisted signal inputs and the latest outcome rows."""
    if _supabase_credentials():
        query = urllib.parse.urlencode(
            {"select": "record,outcome", "order": "signal_timestamp.asc"},
            safe="*,().:_",
        )
        rows = _supabase_request("GET", query)
    else:
        try:
            with _connect() as connection:
                rows = [
                    {
                        "record": json.loads(row["record_json"]),
                        "outcome": (
                            json.loads(row["outcome_json"]) if row["outcome_json"] else None
                        ),
                    }
                    for row in connection.execute("""
                        SELECT record_json, outcome_json
                        FROM ai_signal_history
                        ORDER BY signal_timestamp ASC
                        """).fetchall()
                ]
        except (sqlite3.Error, ValueError, TypeError) as exc:
            raise SignalHistoryStoreError("Could not load AI signal history from SQLite.") from exc

    records: list[SignalRecord] = []
    outcome_rows: list[dict[str, Any]] = []
    for row in rows:
        record_payload = row.get("record")
        if not isinstance(record_payload, dict):
            continue
        try:
            record = _record_from_payload(record_payload)
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Skipping malformed persisted signal record: %s", exc)
            continue
        records.append(record)
        outcome = row.get("outcome")
        if isinstance(outcome, dict):
            outcome_rows.append(outcome)
        else:
            pending = attach_outcomes([record], {})
            if not pending.empty:
                outcome_rows.append(pending.iloc[0].to_dict())

    return records, pd.DataFrame(outcome_rows)
