"""Strict input validation for historical OHLCV research data."""

from __future__ import annotations

import math

import pandas as pd

_REQUIRED = ("timestamp", "open", "high", "low", "close")


def validate_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate chronological candles and return a defensive copy."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("OHLCV input must be a pandas DataFrame.")
    missing = [column for column in _REQUIRED if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required OHLCV columns: {', '.join(missing)}.")
    if frame.empty:
        raise ValueError("OHLCV input must contain at least one candle.")
    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], errors="coerce")
    if result["timestamp"].isna().any():
        raise ValueError("Timestamps must be valid and non-null.")
    if result["timestamp"].duplicated().any():
        raise ValueError("Duplicate candle timestamps are not allowed.")
    if not result["timestamp"].is_monotonic_increasing:
        raise ValueError("Candles must be in chronological order.")
    for column in ("open", "high", "low", "close"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
        if result[column].isna().any() or not result[column].map(math.isfinite).all():
            raise ValueError(f"{column} values must be finite and non-null.")
        if (result[column] <= 0).any():
            raise ValueError(f"{column} values must be positive.")
    invalid = (result["high"] < result[["open", "close", "low"]].max(axis=1)) | (
        result["low"] > result[["open", "close", "high"]].min(axis=1)
    )
    if invalid.any():
        raise ValueError("OHLC relationships are invalid for one or more candles.")
    return result.reset_index(drop=True)
