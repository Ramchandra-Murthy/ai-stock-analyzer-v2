"""Helpers for detecting descriptive intraday scan changes."""

# fmt: off

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

DEFAULT_PRICE_CHANGE_DELTA = 1.0
DEFAULT_VOLUME_SURGE_DELTA = 0.5
DEFAULT_SCORE_DELTA = 10.0


def detect_intraday_alerts(
    previous: pd.DataFrame | None,
    current: pd.DataFrame | None,
    observed_at: datetime,
    price_change_delta: float = DEFAULT_PRICE_CHANGE_DELTA,
    volume_surge_delta: float = DEFAULT_VOLUME_SURGE_DELTA,
    score_delta: float = DEFAULT_SCORE_DELTA,
) -> list[dict[str, Any]]:
    """Return timestamped alerts describing changes between two scan snapshots."""
    previous_rows = _snapshot(previous)
    current_rows = _snapshot(current)
    alerts: list[dict[str, Any]] = []

    previous_keys = set(previous_rows)
    current_keys = set(current_rows)

    for key in sorted(current_keys - previous_keys):
        row = current_rows[key]
        alerts.append(
            _alert(
                observed_at,
                key,
                "NEW_CANDIDATE",
                row,
                "Candidate entered the latest scan.",
            )
        )

    for key in sorted(previous_keys - current_keys):
        row = previous_rows[key]
        alerts.append(
            _alert(
                observed_at,
                key,
                "REMOVED_CANDIDATE",
                row,
                "Candidate left the latest scan.",
            )
        )

    for key in sorted(previous_keys & current_keys):
        before = previous_rows[key]
        after = current_rows[key]
        symbol, exchange = key

        price_delta = _number(after.get("5-min change %")) - _number(
            before.get("5-min change %")
        )
        if abs(price_delta) >= price_change_delta:
            alerts.append(
                _alert(
                    observed_at,
                    key,
                    "PRICE_CHANGE",
                    after,
                    f"{symbol} {exchange} 5-min change moved by {price_delta:+.2f} percentage points.",
                )
            )

        volume_delta = _number(after.get("Volume surge x")) - _number(
            before.get("Volume surge x")
        )
        if abs(volume_delta) >= volume_surge_delta:
            alerts.append(
                _alert(
                    observed_at,
                    key,
                    "VOLUME_CHANGE",
                    after,
                    f"{symbol} {exchange} volume surge changed by {volume_delta:+.2f}x.",
                )
            )

        score_delta_value = _number(after.get("Composite score")) - _number(
            before.get("Composite score")
        )
        if abs(score_delta_value) >= score_delta:
            alerts.append(
                _alert(
                    observed_at,
                    key,
                    "SCORE_CHANGE",
                    after,
                    f"{symbol} {exchange} composite score moved by {score_delta_value:+.1f}.",
                )
            )

        before_state = str(before.get("Plan state", ""))
        after_state = str(after.get("Plan state", ""))
        if before_state != after_state:
            alerts.append(
                _alert(
                    observed_at,
                    key,
                    "STATE_CHANGE",
                    after,
                    f"{symbol} {exchange} setup state changed from "
                    f"{before_state or 'unknown'} to {after_state or 'unknown'}.",
                )
            )

    return alerts


def append_alert_history(
    history: list[dict[str, Any]] | None,
    alerts: list[dict[str, Any]],
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Append alerts and retain the most recent entries."""
    combined = list(history or []) + list(alerts)
    return combined[-limit:]


def alert_history_frame(history: list[dict[str, Any]] | None) -> pd.DataFrame:
    """Return alert history as a stable display dataframe."""
    columns = ["Timestamp", "Symbol", "Exchange", "Alert", "Message"]
    frame = pd.DataFrame(history or [])
    if frame.empty:
        return pd.DataFrame(columns=columns)
    return frame.reindex(columns=columns)


def _snapshot(frame: pd.DataFrame | None) -> dict[tuple[str, str], dict[str, Any]]:
    """Normalize a scan dataframe into a keyed snapshot."""
    if frame is None or frame.empty or "Symbol" not in frame.columns:
        return {}

    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in frame.to_dict(orient="records"):
        symbol = str(row.get("Symbol", "")).strip()
        exchange = str(row.get("Exchange", "")).strip()
        if symbol:
            result[(symbol, exchange)] = row
    return result


def _number(value: Any) -> float:
    """Convert a scalar to float without raising on missing values."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _alert(
    observed_at: datetime,
    key: tuple[str, str],
    alert_type: str,
    row: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    """Build one normalized alert record."""
    return {
        "Timestamp": observed_at.isoformat(),
        "Symbol": key[0],
        "Exchange": key[1],
        "Alert": alert_type,
        "Message": message,
    }
