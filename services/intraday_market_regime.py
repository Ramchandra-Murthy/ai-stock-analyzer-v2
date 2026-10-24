"""Descriptive intraday market-regime metrics from OHLCV data."""

from __future__ import annotations

from typing import Any

import pandas as pd


def classify_market_regime(
    frame: pd.DataFrame | None,
    *,
    trend_threshold_pct: float = 0.5,
    volatility_window: int = 10,
) -> dict[str, Any]:
    """Classify observed trend, volatility and volume conditions."""
    if frame is None or frame.empty:
        return {}
    data = frame.copy()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    required = {"Close", "High", "Low", "Volume"}
    if not required.issubset(data.columns):
        return {}
    data = data.dropna(subset=list(required))
    if len(data) < 2:
        return {}

    close = pd.to_numeric(data["Close"], errors="coerce")
    high = pd.to_numeric(data["High"], errors="coerce")
    low = pd.to_numeric(data["Low"], errors="coerce")
    volume = pd.to_numeric(data["Volume"], errors="coerce")
    if close.isna().all():
        return {}

    first_close = float(close.iloc[0])
    last_close = float(close.iloc[-1])
    change_pct = (last_close - first_close) / first_close * 100 if first_close else 0.0
    if change_pct >= trend_threshold_pct:
        trend = "TRENDING UP"
    elif change_pct <= -trend_threshold_pct:
        trend = "TRENDING DOWN"
    else:
        trend = "RANGE"

    returns = close.pct_change().dropna() * 100
    rolling_vol = float(returns.tail(max(2, volatility_window)).std()) if not returns.empty else 0.0
    if rolling_vol >= 1.0:
        volatility = "HIGH"
    elif rolling_vol >= 0.3:
        volatility = "NORMAL"
    else:
        volatility = "LOW"

    median_volume = float(volume.median())
    latest_volume = float(volume.iloc[-1])
    volume_ratio = latest_volume / median_volume if median_volume > 0 else 0.0
    if volume_ratio >= 1.5:
        volume_state = "ELEVATED"
    elif volume_ratio >= 0.75:
        volume_state = "NORMAL"
    else:
        volume_state = "QUIET"

    range_pct = (
        float(((high - low) / close * 100).tail(max(2, volatility_window)).mean())
        if not close.eq(0).all()
        else 0.0
    )
    return {
        "Trend regime": trend,
        "Trend change %": round(change_pct, 2),
        "Volatility regime": volatility,
        "Recent volatility %": round(rolling_vol, 2),
        "Volume regime": volume_state,
        "Latest/median volume x": round(volume_ratio, 2),
        "Average candle range %": round(range_pct, 2),
    }


def classify_scan_regime(frame: pd.DataFrame | None) -> dict[str, Any]:
    """Summarize observed breadth and volume conditions from scanner results."""
    if frame is None or frame.empty:
        return {}
    change = pd.to_numeric(frame.get("5-min change %"), errors="coerce").dropna()
    volume = pd.to_numeric(frame.get("Volume surge x"), errors="coerce").dropna()
    if change.empty:
        return {}
    average_change = float(change.mean())
    positive_rate = float((change > 0).mean() * 100)
    average_volume = float(volume.mean()) if not volume.empty else 0.0
    if average_change >= 0.5 and positive_rate >= 60:
        breadth = "BULLISH BREADTH"
    elif average_change <= -0.5 and positive_rate <= 40:
        breadth = "BEARISH BREADTH"
    else:
        breadth = "MIXED / RANGE BREADTH"
    volume_state = (
        "ELEVATED" if average_volume >= 1.5 else "NORMAL" if average_volume >= 0.75 else "QUIET"
    )
    return {
        "Breadth regime": breadth,
        "Average 5-min change %": round(average_change, 2),
        "Positive candidates %": round(positive_rate, 2),
        "Average volume surge x": round(average_volume, 2),
        "Volume regime": volume_state,
        "Candidates": int(len(frame)),
    }
