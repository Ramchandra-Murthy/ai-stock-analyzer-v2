"""Technical indicator scoring service."""

from __future__ import annotations

import math


def _valid_number(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def calculate_technical_score(df):
    """Calculate a bounded 0-100 technical component score."""
    if df is None or getattr(df, "empty", True):
        return None, ["Historical price data is unavailable"]

    score = 50
    reasons = []
    observed_components = 0
    latest = df.iloc[-1]

    if "RSI" in latest.index and _valid_number(latest["RSI"]):
        rsi = float(latest["RSI"])
        if 0.0 <= rsi <= 100.0:
            observed_components += 1
            if rsi < 30:
                score += 15
                reasons.append(f"RSI is oversold at {rsi:.1f}")
            elif rsi > 70:
                score -= 15
                reasons.append(f"RSI is overbought at {rsi:.1f}")
            else:
                score += 5
                reasons.append(f"RSI is neutral at {rsi:.1f}")
        else:
            reasons.append("RSI data is outside the valid 0-100 range")
    else:
        reasons.append("RSI data is unavailable")

    if (
        "EMA20" in latest.index
        and "EMA50" in latest.index
        and _valid_number(latest["EMA20"])
        and _valid_number(latest["EMA50"])
    ):
        observed_components += 1
        ema20, ema50 = float(latest["EMA20"]), float(latest["EMA50"])
        if ema20 > ema50:
            score += 10
            reasons.append("EMA20 is above EMA50, indicating short-term bullish momentum")
        elif ema20 < ema50:
            score -= 5
            reasons.append("EMA20 is below EMA50, indicating short-term weakness")
        else:
            reasons.append("EMA20 is equal to EMA50")

    if (
        "EMA50" in latest.index
        and "EMA200" in latest.index
        and _valid_number(latest["EMA50"])
        and _valid_number(latest["EMA200"])
    ):
        observed_components += 1
        ema50, ema200 = float(latest["EMA50"]), float(latest["EMA200"])
        if ema50 > ema200:
            score += 10
            reasons.append("EMA50 is above EMA200, indicating a bullish long-term trend")
        elif ema50 < ema200:
            score -= 10
            reasons.append("EMA50 is below EMA200, indicating a bearish long-term trend")
        else:
            reasons.append("EMA50 is equal to EMA200")

    if (
        "MACD" in latest.index
        and "MACD_Signal" in latest.index
        and _valid_number(latest["MACD"])
        and _valid_number(latest["MACD_Signal"])
    ):
        observed_components += 1
        macd, signal = float(latest["MACD"]), float(latest["MACD_Signal"])
        if macd > signal:
            score += 10
            reasons.append("MACD is above its signal line, indicating bullish momentum")
        elif macd < signal:
            score -= 10
            reasons.append("MACD is below its signal line, indicating bearish momentum")
        else:
            reasons.append("MACD is equal to its signal line")
    else:
        reasons.append("MACD data is unavailable")

    if (
        "Close" in latest.index
        and "Resistance" in latest.index
        and _valid_number(latest["Close"])
        and _valid_number(latest["Resistance"])
    ):
        observed_components += 1
        close, resistance = float(latest["Close"]), float(latest["Resistance"])
        if close > resistance:
            score += 10
            reasons.append("Price has broken above resistance")
        else:
            reasons.append("Price remains below resistance")

    if (
        "Close" in latest.index
        and "Support" in latest.index
        and _valid_number(latest["Close"])
        and _valid_number(latest["Support"])
    ):
        observed_components += 1
        close, support = float(latest["Close"]), float(latest["Support"])
        if close > support:
            score += 5
            reasons.append("Price is trading above support")
        elif close < support:
            score -= 10
            reasons.append("Price is trading below support")
        else:
            reasons.append("Price is trading at support")

    if observed_components == 0:
        return None, ["Insufficient technical indicators for scoring"]

    return max(0, min(round(score), 100)), reasons
