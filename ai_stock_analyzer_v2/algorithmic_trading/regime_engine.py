"""Regime detection for Indian equities."""

from __future__ import annotations

import pandas as pd


def _series(frame: pd.DataFrame, name: str) -> pd.Series:
    if name not in frame:
        raise ValueError(f"missing required column: {name}")
    return pd.to_numeric(frame[name], errors="coerce")


def regime_score(frame: pd.DataFrame, lookback: int = 20) -> int:
    """Composite score using breakout, MA trend and price structure."""
    if len(frame) < max(lookback + 2, 50):
        return 0

    close = _series(frame, "Close")
    high = _series(frame, "High")
    low = _series(frame, "Low")
    ema_fast = close.ewm(span=20, adjust=False).mean()
    ema_slow = close.ewm(span=50, adjust=False).mean()
    prior_high = high.shift(1).rolling(lookback).max()
    prior_low = low.shift(1).rolling(lookback).min()

    score = 0
    score += int(close.iloc[-1] > ema_fast.iloc[-1])
    score += int(ema_fast.iloc[-1] > ema_slow.iloc[-1])
    score += int(close.iloc[-1] > prior_high.iloc[-1])
    score += int(high.iloc[-1] > high.iloc[-2] and low.iloc[-1] > low.iloc[-2])
    score -= int(close.iloc[-1] < ema_fast.iloc[-1])
    score -= int(ema_fast.iloc[-1] < ema_slow.iloc[-1])
    score -= int(close.iloc[-1] < prior_low.iloc[-1])
    score -= int(high.iloc[-1] < high.iloc[-2] and low.iloc[-1] < low.iloc[-2])
    return score


def classify_regime(frame: pd.DataFrame, lookback: int = 20) -> str:
    score = regime_score(frame, lookback)
    if score >= 3:
        return "BULLISH"
    if score <= -3:
        return "BEARISH"
    return "INCONCLUSIVE"
