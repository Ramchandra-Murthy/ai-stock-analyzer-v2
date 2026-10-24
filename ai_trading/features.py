"""Feature engineering for the AI trading intelligence engine."""

from __future__ import annotations

import pandas as pd


def build_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Build normalized, model-ready market features from OHLCV data."""
    required = {"Close"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    close = pd.to_numeric(frame["Close"], errors="coerce")
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
