"""Feature engineering for the AI trading intelligence engine."""

from __future__ import annotations

import pandas as pd


def adjusted_close_series(frame: pd.DataFrame) -> pd.Series:
    """Use Yahoo's split/dividend-adjusted close when it is available."""
    column = "Adj Close" if "Adj Close" in frame.columns else "Close"
    if column not in frame.columns:
        raise ValueError("market data must contain Close or Adj Close")
    return pd.to_numeric(frame[column], errors="coerce")


def adjusted_ohlc_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply the adjusted-close factor consistently to raw OHLC fields."""
    if "Adj Close" not in frame.columns or "Close" not in frame.columns:
        return frame.copy()
    raw_close = pd.to_numeric(frame["Close"], errors="coerce")
    adjusted_close = adjusted_close_series(frame)
    factor = adjusted_close.div(raw_close.where(raw_close.gt(0.0)))
    result = frame.copy()
    for column in ("Open", "High", "Low", "Close"):
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce") * factor
    return result


def build_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Build normalized, model-ready market features from OHLCV data."""
    required = {"Close"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    close = adjusted_close_series(frame)
    features = pd.DataFrame(index=frame.index)
    features["return_1"] = close.pct_change()
    features["return_5"] = close.pct_change(5)
    features["return_20"] = close.pct_change(20)
    features["ema_gap"] = (
        close.ewm(span=20, adjust=False).mean() / close.ewm(span=50, adjust=False).mean() - 1.0
    )
    features["volatility_20"] = close.pct_change().rolling(20).std()

    if "Volume" in frame.columns:
        volume = pd.to_numeric(frame["Volume"], errors="coerce")
        volume_mean = volume.rolling(20).mean()
        features["volume_ratio"] = volume / volume_mean.replace(0, pd.NA)
    else:
        features["volume_ratio"] = 1.0

    return features.replace([float("inf"), float("-inf")], pd.NA).dropna()
