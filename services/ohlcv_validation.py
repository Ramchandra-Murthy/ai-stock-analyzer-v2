"""Shared validation for provider OHLCV frames."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

import pandas as pd

REQUIRED_OHLCV_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


def validate_ohlcv_frame(frame: pd.DataFrame | None) -> tuple[pd.DataFrame, list[str]]:
    """Return a normalized frame and validation errors; invalid frames are not repaired."""
    if frame is None or frame.empty:
        return pd.DataFrame(), ["empty frame"]
    missing = [name for name in REQUIRED_OHLCV_COLUMNS if name not in frame.columns]
    if missing:
        return pd.DataFrame(), [f"missing columns: {', '.join(missing)}"]

    data = frame.loc[:, REQUIRED_OHLCV_COLUMNS].copy()
    data = data.apply(pd.to_numeric, errors="coerce")
    errors: list[str] = []
    if data.isna().any().any():
        errors.append("missing or nonnumeric OHLCV values")
    if not data.apply(lambda col: col.map(lambda value: math.isfinite(float(value)))).all().all():
        errors.append("non-finite OHLCV values")
    prices = data[["Open", "High", "Low", "Close"]]
    if (prices <= 0).any().any():
        errors.append("nonpositive price")
    if (data["Volume"] < 0).any():
        errors.append("negative volume")
    if (
        (data["High"] < data[["Open", "Close", "Low"]].max(axis=1))
        | (data["Low"] > data[["Open", "Close", "High"]].min(axis=1))
    ).any():
        errors.append("invalid OHLC relationship")
    if data.index.has_duplicates:
        errors.append("duplicate timestamps")
    if errors:
        return pd.DataFrame(), list(dict.fromkeys(errors))
    return data.sort_index(), []


def build_data_status(
    frame: pd.DataFrame | None,
    *,
    source: str,
    retrieved_at: datetime | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    """Create explicit provider, retrieval, bar-time and validation metadata."""
    retrieved = retrieved_at or datetime.now(UTC)
    last_bar = frame.index[-1] if frame is not None and not frame.empty else None
    problems = list(errors or [])
    return {
        "source": source,
        "retrieved_at": retrieved.isoformat(),
        "last_bar": last_bar.isoformat() if hasattr(last_bar, "isoformat") else None,
        "status": "VALID" if frame is not None and not frame.empty and not problems else "INVALID",
        "row_count": len(frame) if frame is not None else 0,
        "validation_errors": problems,
    }
