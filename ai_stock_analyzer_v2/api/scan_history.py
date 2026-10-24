"""Small SQLite persistence layer for EROS scan results."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS scan_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    count INTEGER NOT NULL,
    results_json TEXT NOT NULL,
    stats_json TEXT NOT NULL
)
"""

INSERT_SCAN_SQL = """
INSERT INTO scan_history
    (job_id, completed_at, count, results_json, stats_json)
VALUES (?, ?, ?, ?, ?)
"""

SELECT_RECENT_SQL = """
SELECT job_id, completed_at, count, results_json, stats_json
FROM scan_history
ORDER BY id DESC
LIMIT ?
"""


def _db_path() -> Path:
    """Return the configurable EROS SQLite database path."""
    return Path(os.getenv("EROS_SCAN_DB", "data/eros_scans.sqlite3"))


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(CREATE_TABLE_SQL)
    return connection


def save_completed_scan(
    job_id: str,
    completed_at: str,
    results: list[dict[str, Any]],
    scan_stats: dict[str, Any],
) -> None:
    """Persist one completed scan result."""
    values = (
        job_id,
        completed_at,
        len(results),
        json.dumps(results, default=str),
        json.dumps(scan_stats, default=str),
    )
    with _connect() as connection:
        connection.execute(INSERT_SCAN_SQL, values)


def recent_scans(limit: int = 20) -> list[dict[str, Any]]:
    """Return the most recent completed scans."""
    with _connect() as connection:
        rows = connection.execute(SELECT_RECENT_SQL, (limit,)).fetchall()

    return [
        {
            "job_id": row[0],
            "completed_at": row[1],
            "count": row[2],
            "results": json.loads(row[3]),
            "scan_stats": json.loads(row[4]),
        }
        for row in rows
    ]
