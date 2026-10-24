import math

import pandas as pd


def _safe_float(value, default=None):
    """Convert a value to a finite float safely."""
    try:
        number = float(value)
        if not math.isfinite(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def calculate_target_price(history, technical_score=None):
    """Calculate rule-based target, stop, upside, and risk/reward metrics.

    Missing or invalid market inputs never become fabricated trade levels.
    """
    empty_result = {
        "current_price": None,
        "target_price": None,
        "stop_loss": None,
        "upside_percent": None,
        "risk_reward": None,
        "atr": None,
        "status": None,
    }

    if history is None or history.empty:
        empty_result["status"] = "No historical data"
        return empty_result

    required_columns = {"High", "Low", "Close"}
    missing = required_columns.difference(history.columns)
    if missing:
        empty_result["status"] = "Missing columns: " + ", ".join(sorted(missing))
        return empty_result

    df = history.copy()
    for column in required_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=["High", "Low", "Close"])
    df = df[
        (df["High"] > 0)
        & (df["Low"] > 0)
        & (df["Close"] > 0)
        & (df["High"] >= df["Low"])
        & (df["Close"] <= df["High"])
        & (df["Close"] >= df["Low"])
    ]

    if len(df) < 14:
        empty_result["status"] = "Insufficient valid historical data"
        return empty_result

    current_price = _safe_float(df["Close"].iloc[-1])
    if current_price is None or current_price <= 0:
        empty_result["status"] = "Invalid current price"
        return empty_result

    previous_close = df["Close"].shift(1)
    true_range = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - previous_close).abs(),
            (df["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr_series = true_range.rolling(window=14, min_periods=14).mean()
    atr = _safe_float(atr_series.iloc[-1])
    if atr is None or atr <= 0 or not math.isfinite(atr):
        return {
            "current_price": round(current_price, 2),
            "target_price": None,
            "stop_loss": None,
            "upside_percent": None,
            "risk_reward": None,
            "atr": None,
            "status": "ATR unavailable",
        }

    score = _safe_float(technical_score)
    if score is None:
        return {
            "current_price": round(current_price, 2),
            "target_price": None,
            "stop_loss": None,
            "upside_percent": None,
            "risk_reward": None,
            "atr": round(atr, 2),
            "status": "Insufficient technical evidence",
        }

    if score < 0 or score > 100:
        return {
            "current_price": round(current_price, 2),
            "target_price": None,
            "stop_loss": None,
            "upside_percent": None,
            "risk_reward": None,
            "atr": round(atr, 2),
            "status": "Invalid technical score",
        }

    if score >= 80:
        target_atr_multiplier = 3.0
    elif score >= 65:
        target_atr_multiplier = 2.5
    elif score >= 50:
        target_atr_multiplier = 2.0
    else:
        target_atr_multiplier = 1.5

    target_price = current_price + atr * target_atr_multiplier
    stop_loss = max(current_price - atr * 1.5, 0.0)
    reward = target_price - current_price
    risk = current_price - stop_loss
    upside_percent = reward / current_price * 100
    risk_reward = reward / risk if risk > 0 else None

    if not all(math.isfinite(value) for value in (target_price, stop_loss, reward, upside_percent)):
        return {
            "current_price": round(current_price, 2),
            "target_price": None,
            "stop_loss": None,
            "upside_percent": None,
            "risk_reward": None,
            "atr": round(atr, 2),
            "status": "Non-finite target calculation",
        }

    if risk_reward is not None and not math.isfinite(risk_reward):
        risk_reward = None

    return {
        "current_price": round(current_price, 2),
        "target_price": round(target_price, 2),
        "stop_loss": round(stop_loss, 2),
        "upside_percent": round(upside_percent, 2),
        "risk_reward": round(risk_reward, 2) if risk_reward is not None else None,
        "atr": round(atr, 2),
        "status": "OK",
    }
