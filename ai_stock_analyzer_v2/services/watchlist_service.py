"""Persistent storage for the app's single personal watchlist.

This app intentionally uses one shared, unauthenticated watchlist because it is
operated as a single-user personal tool. Anyone who can access the deployed app
can also access and change these records; do not use this mode for sensitive data.
Set WATCHLIST_DATABASE_PATH to a durable writable path in deployed environments.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DATABASE_PATH = Path("data/watchlists.sqlite3")
OWNER_ID = "local-owner"
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,31}$")
ALLOWED_STATUSES = {"Watching", "Bought", "Sold", "Avoid"}
ALLOWED_TYPES = {"Delivery", "Swing", "Intraday", "Investment", "Options", "Other"}
DETAIL_FIELDS = (
    "entry_price",
    "stop_loss",
    "target_price",
    "quantity",
    "investment_type",
    "purchase_date",
    "notes",
    "status",
    "asset_category",
    "asset_details",
)


class WatchlistError(ValueError):
    """Raised when a watchlist operation receives invalid input."""


def _database_path() -> Path:
    return Path(os.environ.get("WATCHLIST_DATABASE_PATH", str(DEFAULT_DATABASE_PATH)))


def _require_user_id(user_id: str) -> str:
    """Retain the service API while routing all operations to the single owner."""
    if not isinstance(user_id, str) or not user_id.strip():
        raise WatchlistError("A watchlist owner is required.")
    return OWNER_ID


def _connect() -> sqlite3.Connection:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS watchlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, name)
        );
        CREATE TABLE IF NOT EXISTS watchlist_symbols (
            watchlist_id INTEGER NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
            symbol TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            entry_price REAL,
            stop_loss REAL,
            target_price REAL,
            quantity INTEGER,
            investment_type TEXT NOT NULL DEFAULT 'Watching',
            purchase_date TEXT,
            notes TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Watching',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            asset_category TEXT NOT NULL DEFAULT 'Stocks / F&O',
            asset_details TEXT NOT NULL DEFAULT '{}',
            PRIMARY KEY (watchlist_id, symbol)
        );
        CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON watchlists(user_id);
        CREATE TABLE IF NOT EXISTS watchlist_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    # Upgrade databases created by earlier versions without losing saved symbols.
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(watchlist_symbols)")}
    migrations = {
        "entry_price": "REAL",
        "stop_loss": "REAL",
        "target_price": "REAL",
        "quantity": "INTEGER",
        "investment_type": "TEXT NOT NULL DEFAULT 'Watching'",
        "purchase_date": "TEXT",
        "notes": "TEXT NOT NULL DEFAULT ''",
        "status": "TEXT NOT NULL DEFAULT 'Watching'",
        "updated_at": "TEXT",
        "asset_category": "TEXT NOT NULL DEFAULT 'Stocks / F&O'",
        "asset_details": "TEXT NOT NULL DEFAULT '{}'",
    }
    for name, definition in migrations.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE watchlist_symbols ADD COLUMN {name} {definition}")
    # Consolidate any pre-existing per-user lists into one list, preserving
    # symbols and their saved details. Existing duplicate symbols keep the first row.
    migrated = connection.execute(
        "SELECT 1 FROM watchlist_meta WHERE key = 'single_owner_v1'"
    ).fetchone()
    existing_lists = (
        connection.execute("SELECT id FROM watchlists ORDER BY created_at, id").fetchall()
        if migrated is None
        else []
    )
    if existing_lists:
        target_id = int(existing_lists[0]["id"])
        for old_list in existing_lists[1:]:
            old_id = int(old_list["id"])
            connection.execute(
                """
                INSERT OR IGNORE INTO watchlist_symbols (
                    watchlist_id, symbol, position, created_at, entry_price, stop_loss,
                    target_price, quantity, investment_type, purchase_date, notes, status,
                    updated_at
                )
                SELECT ?, symbol, position, created_at, entry_price, stop_loss,
                       target_price, quantity, investment_type, purchase_date, notes, status,
                       updated_at
                FROM watchlist_symbols WHERE watchlist_id = ?
                """,
                (target_id, old_id),
            )
        connection.execute("DELETE FROM watchlists WHERE id != ?", (target_id,))
        connection.execute(
            "UPDATE watchlists SET user_id = ?, name = ? WHERE id = ?",
            (OWNER_ID, "My Watchlist", target_id),
        )
    if migrated is None:
        connection.execute(
            "INSERT INTO watchlist_meta (key, value) VALUES ('single_owner_v1', 'done')"
        )
    connection.commit()
    return connection


def _require_name(name: str) -> str:
    normalized = name.strip() if isinstance(name, str) else ""
    if not normalized or len(normalized) > 80:
        raise WatchlistError("Watchlist name must contain 1 to 80 characters.")
    return normalized


def _require_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper() if isinstance(symbol, str) else ""
    if not SYMBOL_PATTERN.fullmatch(normalized) or normalized.endswith(".") or ".." in normalized:
        raise WatchlistError("Enter a valid stock symbol.")
    return normalized


def _sqlite_list_watchlists(user_id: str) -> list[dict[str, Any]]:
    owner = _require_user_id(user_id)
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT w.id, w.name, w.created_at, COUNT(s.symbol) AS symbol_count
            FROM watchlists AS w
            LEFT JOIN watchlist_symbols AS s ON s.watchlist_id = w.id
            WHERE w.user_id = ?
            GROUP BY w.id
            ORDER BY w.created_at, w.id
            """,
            (owner,),
        ).fetchall()
    return [dict(row) for row in rows]


def _sqlite_create_watchlist(user_id: str, name: str) -> int:
    owner = _require_user_id(user_id)
    normalized_name = _require_name(name)
    try:
        with _connect() as connection:
            cursor = connection.execute(
                "INSERT INTO watchlists (user_id, name) VALUES (?, ?)",
                (owner, normalized_name),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as exc:
        raise WatchlistError("A watchlist with that name already exists.") from exc


def _sqlite_rename_watchlist(user_id: str, watchlist_id: int, name: str) -> None:
    owner = _require_user_id(user_id)
    normalized_name = _require_name(name)
    try:
        with _connect() as connection:
            cursor = connection.execute(
                "UPDATE watchlists SET name = ? WHERE id = ? AND user_id = ?",
                (normalized_name, watchlist_id, owner),
            )
            if cursor.rowcount == 0:
                raise WatchlistError("Watchlist not found.")
    except sqlite3.IntegrityError as exc:
        raise WatchlistError("A watchlist with that name already exists.") from exc


def _sqlite_delete_watchlist(user_id: str, watchlist_id: int) -> None:
    owner = _require_user_id(user_id)
    with _connect() as connection:
        cursor = connection.execute(
            "DELETE FROM watchlists WHERE id = ? AND user_id = ?",
            (watchlist_id, owner),
        )
        if cursor.rowcount == 0:
            raise WatchlistError("Watchlist not found.")


def _sqlite_list_symbols(user_id: str, watchlist_id: int) -> list[str]:
    owner = _require_user_id(user_id)
    with _connect() as connection:
        watchlist = connection.execute(
            "SELECT id FROM watchlists WHERE id = ? AND user_id = ?",
            (watchlist_id, owner),
        ).fetchone()
        if watchlist is None:
            raise WatchlistError("Watchlist not found.")
        rows = connection.execute(
            "SELECT symbol FROM watchlist_symbols WHERE watchlist_id = ? ORDER BY position, symbol",
            (watchlist_id,),
        ).fetchall()
    return [str(row["symbol"]) for row in rows]


def _sqlite_list_stock_records(user_id: str, watchlist_id: int) -> list[dict[str, Any]]:
    """Return saved symbols and all manually entered investment diary details."""
    owner = _require_user_id(user_id)
    with _connect() as connection:
        watchlist = connection.execute(
            "SELECT id FROM watchlists WHERE id = ? AND user_id = ?",
            (watchlist_id, owner),
        ).fetchone()
        if watchlist is None:
            raise WatchlistError("Watchlist not found.")
        rows = connection.execute(
            """
            SELECT symbol, entry_price, stop_loss, target_price, quantity,
                   investment_type, purchase_date, notes, status, created_at, updated_at,
                   asset_category, asset_details
            FROM watchlist_symbols
            WHERE watchlist_id = ?
            ORDER BY position, symbol
            """,
            (watchlist_id,),
        ).fetchall()
    records = [dict(row) for row in rows]
    for record in records:
        try:
            record["asset_details"] = json.loads(record.get("asset_details") or "{}")
        except (TypeError, ValueError):
            record["asset_details"] = {}
        record.setdefault("asset_category", "Stocks / F&O")
    return records


def _sqlite_add_symbol(
    user_id: str, watchlist_id: int, symbol: str, details: dict[str, Any] | None = None
) -> bool:
    owner = _require_user_id(user_id)
    normalized_symbol = _require_symbol(symbol)
    details = details or {}
    _validate_details(details)
    with _connect() as connection:
        watchlist = connection.execute(
            "SELECT id FROM watchlists WHERE id = ? AND user_id = ?",
            (watchlist_id, owner),
        ).fetchone()
        if watchlist is None:
            raise WatchlistError("Watchlist not found.")
        existing = connection.execute(
            "SELECT 1 FROM watchlist_symbols WHERE watchlist_id = ? AND symbol = ?",
            (watchlist_id, normalized_symbol),
        ).fetchone()
        if existing:
            return False
        position = connection.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM watchlist_symbols WHERE watchlist_id = ?",
            (watchlist_id,),
        ).fetchone()[0]
        fields = {field: details.get(field) for field in DETAIL_FIELDS}
        fields["investment_type"] = fields["investment_type"] or "Other"
        fields["status"] = fields["status"] or "Watching"
        fields["notes"] = fields["notes"] or ""
        connection.execute(
            """
            INSERT INTO watchlist_symbols (
                watchlist_id, symbol, position, entry_price, stop_loss, target_price,
                quantity, investment_type, purchase_date, notes, status, asset_category, asset_details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                watchlist_id,
                normalized_symbol,
                position,
                fields["entry_price"],
                fields["stop_loss"],
                fields["target_price"],
                fields["quantity"],
                fields["investment_type"],
                fields["purchase_date"],
                fields["notes"],
                fields["status"],
                fields.get("asset_category") or "Stocks / F&O",
                json.dumps(fields.get("asset_details") or {}, default=str),
            ),
        )
    return True


def _validate_details(details: dict[str, Any]) -> None:
    for field in ("entry_price", "stop_loss", "target_price"):
        value = details.get(field)
        if value is not None and value != "" and float(value) < 0:
            raise WatchlistError(f"{field.replace('_', ' ').title()} cannot be negative.")
    quantity = details.get("quantity")
    if quantity is not None and quantity != "" and int(quantity) < 1:
        raise WatchlistError("Quantity must be at least 1.")
    if details.get("asset_category") and details["asset_category"] not in {
        "Stocks / F&O",
        "Mutual Funds",
        "Commodity",
        "Currency",
    }:
        raise WatchlistError("Select a valid investment category.")
    if details.get("asset_details") is not None and not isinstance(
        details.get("asset_details"), dict
    ):
        raise WatchlistError("Instrument details must be a structured object.")
    investment_type = details.get("investment_type")
    if investment_type and investment_type not in ALLOWED_TYPES:
        raise WatchlistError("Select a valid investment type.")
    status = details.get("status")
    if status and status not in ALLOWED_STATUSES:
        raise WatchlistError("Select a valid stock status.")


def _sqlite_update_stock_details(
    user_id: str, watchlist_id: int, symbol: str, details: dict[str, Any]
) -> None:
    owner = _require_user_id(user_id)
    normalized_symbol = _require_symbol(symbol)
    _validate_details(details)
    fields = {field: details.get(field) for field in DETAIL_FIELDS}
    fields["investment_type"] = fields["investment_type"] or "Other"
    fields["status"] = fields["status"] or "Watching"
    fields["notes"] = fields["notes"] or ""
    with _connect() as connection:
        cursor = connection.execute(
            """
            UPDATE watchlist_symbols
            SET entry_price = ?, stop_loss = ?, target_price = ?, quantity = ?,
                investment_type = ?, purchase_date = ?, notes = ?, status = ?,
                asset_category = ?, asset_details = ?, updated_at = CURRENT_TIMESTAMP
            WHERE watchlist_id = ? AND symbol = ?
              AND EXISTS (SELECT 1 FROM watchlists WHERE id = ? AND user_id = ?)
            """,
            (
                fields["entry_price"],
                fields["stop_loss"],
                fields["target_price"],
                fields["quantity"],
                fields["investment_type"],
                fields["purchase_date"],
                fields["notes"],
                fields["status"],
                fields.get("asset_category") or "Stocks / F&O",
                json.dumps(fields.get("asset_details") or {}, default=str),
                watchlist_id,
                normalized_symbol,
                watchlist_id,
                owner,
            ),
        )
        if cursor.rowcount == 0:
            raise WatchlistError("Stock not found in this watchlist.")


def _sqlite_remove_symbol(user_id: str, watchlist_id: int, symbol: str) -> bool:
    owner = _require_user_id(user_id)
    normalized_symbol = _require_symbol(symbol)
    with _connect() as connection:
        watchlist = connection.execute(
            "SELECT id FROM watchlists WHERE id = ? AND user_id = ?",
            (watchlist_id, owner),
        ).fetchone()
        if watchlist is None:
            raise WatchlistError("Watchlist not found.")
        cursor = connection.execute(
            "DELETE FROM watchlist_symbols WHERE watchlist_id = ? AND symbol = ?",
            (watchlist_id, normalized_symbol),
        )
        return cursor.rowcount > 0


# Supabase REST backend. No third-party SDK is required; this keeps the
# application's dependency lockfile unchanged. Credentials are read only from
# server-side Streamlit secrets or environment variables.


_SUPABASE_WATCHLIST_ID = 1
_SUPABASE_TABLE = "stock_watchlist"


def _supabase_credentials() -> tuple[str, str] | None:
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = (
        os.environ.get("SUPABASE_SECRET_KEY", "").strip()
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    )
    try:
        import streamlit as st

        secrets = st.secrets
        if not url:
            url = str(secrets.get("SUPABASE_URL", "")).strip().rstrip("/")
        if not key:
            key = str(
                secrets.get("SUPABASE_SECRET_KEY", "")
                or secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
            ).strip()
    except Exception:
        # Streamlit may not be installed in service-only tests or CLI scripts.
        pass
    if url and key:
        return url, key
    return None


def _supabase_enabled() -> bool:
    return _supabase_credentials() is not None


def _supabase_request(
    method: str,
    query: str = "",
    payload: dict[str, Any] | list[dict[str, Any]] | None = None,
    *,
    prefer: str | None = None,
) -> list[dict[str, Any]]:
    credentials = _supabase_credentials()
    if credentials is None:
        raise WatchlistError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SECRET_KEY "
            "in Streamlit secrets or environment variables."
        )
    base_url, secret_key = credentials
    url = f"{base_url}/rest/v1/{_SUPABASE_TABLE}"
    if query:
        url = f"{url}?{query}"
    body = None if payload is None else json.dumps(payload, default=str).encode("utf-8")
    headers = {
        "apikey": secret_key,
        "Authorization": f"Bearer {secret_key}",
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
        # Do not include request headers or secrets in any error surfaced to UI.
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise WatchlistError(
            f"Supabase request failed (HTTP {exc.code}). Check the table schema, "
            "secret key, and database migration. "
            + (detail if exc.code < 500 else "The database service is temporarily unavailable.")
        ) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise WatchlistError(
            "Could not reach Supabase. Check the project URL and network."
        ) from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise WatchlistError("Supabase returned an unreadable response.") from exc


def _supabase_records() -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {"select": "*", "order": "position.asc,symbol.asc"},
        safe="*,().:_",
    )
    return _supabase_request("GET", query)


def _supabase_watchlist_exists(watchlist_id: int) -> None:
    if int(watchlist_id) != _SUPABASE_WATCHLIST_ID:
        raise WatchlistError("Watchlist not found.")


def list_watchlists(user_id: str) -> list[dict[str, Any]]:
    _require_user_id(user_id)
    if not _supabase_enabled():
        return _sqlite_list_watchlists(user_id)
    records = _supabase_records()
    return [
        {
            "id": _SUPABASE_WATCHLIST_ID,
            "name": "My Watchlist",
            "created_at": records[0].get("created_at") if records else None,
            "symbol_count": len(records),
        }
    ]


def create_watchlist(user_id: str, name: str) -> int:
    _require_user_id(user_id)
    if not _supabase_enabled():
        return _sqlite_create_watchlist(user_id, name)
    if _require_name(name) != "My Watchlist":
        raise WatchlistError("Supabase mode supports one personal watchlist named 'My Watchlist'.")
    return _SUPABASE_WATCHLIST_ID


def rename_watchlist(user_id: str, watchlist_id: int, name: str) -> None:
    _require_user_id(user_id)
    if not _supabase_enabled():
        return _sqlite_rename_watchlist(user_id, watchlist_id, name)
    _supabase_watchlist_exists(watchlist_id)
    if _require_name(name) != "My Watchlist":
        raise WatchlistError("The personal Supabase watchlist name is fixed as 'My Watchlist'.")


def delete_watchlist(user_id: str, watchlist_id: int) -> None:
    _require_user_id(user_id)
    if not _supabase_enabled():
        return _sqlite_delete_watchlist(user_id, watchlist_id)
    _supabase_watchlist_exists(watchlist_id)
    raise WatchlistError("The single personal Supabase watchlist cannot be deleted.")


def list_symbols(user_id: str, watchlist_id: int) -> list[str]:
    _require_user_id(user_id)
    if not _supabase_enabled():
        return _sqlite_list_symbols(user_id, watchlist_id)
    _supabase_watchlist_exists(watchlist_id)
    return [str(row.get("symbol", "")) for row in _supabase_records()]


def list_stock_records(user_id: str, watchlist_id: int) -> list[dict[str, Any]]:
    _require_user_id(user_id)
    if not _supabase_enabled():
        return _sqlite_list_stock_records(user_id, watchlist_id)
    _supabase_watchlist_exists(watchlist_id)
    records = _supabase_records()
    for record in records:
        record.setdefault("investment_type", "Other")
        record.setdefault("status", "Watching")
        record.setdefault("notes", "")
        record.setdefault("asset_category", "Stocks / F&O")
        if not isinstance(record.get("asset_details"), dict):
            try:
                record["asset_details"] = json.loads(record.get("asset_details") or "{}")
            except (TypeError, ValueError):
                record["asset_details"] = {}
    return records


def add_symbol(
    user_id: str, watchlist_id: int, symbol: str, details: dict[str, Any] | None = None
) -> bool:
    _require_user_id(user_id)
    if not _supabase_enabled():
        return _sqlite_add_symbol(user_id, watchlist_id, symbol, details)
    _supabase_watchlist_exists(watchlist_id)
    normalized_symbol = _require_symbol(symbol)
    details = details or {}
    _validate_details(details)
    query = urllib.parse.urlencode(
        {"select": "id", "symbol": f"eq.{normalized_symbol}"},
        safe="*,().:_",
    )
    if _supabase_request("GET", query):
        return False
    fields = {field: details.get(field) for field in DETAIL_FIELDS}
    fields["investment_type"] = fields["investment_type"] or "Other"
    fields["status"] = fields["status"] or "Watching"
    fields["notes"] = fields["notes"] or ""
    existing = _supabase_records()
    position = max((int(row.get("position") or 0) for row in existing), default=-1) + 1
    payload = {
        "symbol": normalized_symbol,
        "company_name": normalized_symbol,
        "entry_price": fields["entry_price"] or None,
        "stop_loss": fields["stop_loss"] or None,
        "target_price": fields["target_price"] or None,
        "quantity": fields["quantity"] or None,
        "investment_type": fields["investment_type"],
        "purchase_date": fields["purchase_date"] or None,
        "notes": fields["notes"],
        "status": fields["status"],
        "position": position,
        "asset_category": fields.get("asset_category") or "Stocks / F&O",
        "asset_details": fields.get("asset_details") or {},
    }
    _supabase_request("POST", "select=id", [payload], prefer="return=representation")
    return True


def update_stock_details(
    user_id: str, watchlist_id: int, symbol: str, details: dict[str, Any]
) -> None:
    _require_user_id(user_id)
    if not _supabase_enabled():
        return _sqlite_update_stock_details(user_id, watchlist_id, symbol, details)
    _supabase_watchlist_exists(watchlist_id)
    normalized_symbol = _require_symbol(symbol)
    _validate_details(details)
    fields = {field: details.get(field) for field in DETAIL_FIELDS}
    fields["investment_type"] = fields["investment_type"] or "Other"
    fields["status"] = fields["status"] or "Watching"
    fields["notes"] = fields["notes"] or ""
    payload = {
        "entry_price": fields["entry_price"] or None,
        "stop_loss": fields["stop_loss"] or None,
        "target_price": fields["target_price"] or None,
        "quantity": fields["quantity"] or None,
        "investment_type": fields["investment_type"],
        "purchase_date": fields["purchase_date"] or None,
        "notes": fields["notes"],
        "status": fields["status"],
        "asset_category": fields.get("asset_category") or "Stocks / F&O",
        "asset_details": fields.get("asset_details") or {},
        "updated_at": datetime.now(UTC).isoformat(),
    }
    query = urllib.parse.urlencode(
        {"symbol": f"eq.{normalized_symbol}", "select": "id"},
        safe="*,().:_",
    )
    result = _supabase_request("PATCH", query, payload, prefer="return=representation")
    if not result:
        raise WatchlistError("Stock not found in this watchlist.")


def remove_symbol(user_id: str, watchlist_id: int, symbol: str) -> bool:
    _require_user_id(user_id)
    if not _supabase_enabled():
        return _sqlite_remove_symbol(user_id, watchlist_id, symbol)
    _supabase_watchlist_exists(watchlist_id)
    normalized_symbol = _require_symbol(symbol)
    query = urllib.parse.urlencode(
        {"symbol": f"eq.{normalized_symbol}", "select": "id"},
        safe="*,().:_",
    )
    result = _supabase_request("DELETE", query, prefer="return=representation")
    return bool(result)
