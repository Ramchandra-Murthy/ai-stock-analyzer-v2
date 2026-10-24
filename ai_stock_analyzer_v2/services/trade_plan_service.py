import math

import pandas as pd

from services.market_service import get_latest_available_price


def _safe_float(value):
    """Convert a value to a finite float or return None."""
    try:
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    except (TypeError, ValueError):
        return None


def _clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def generate_trade_plan(
    history: pd.DataFrame, technical_score: float | None = None, symbol: str | None = None
):
    """Generate a technical research trade plan using a canonical market quote when available."""
    if history is None or history.empty:
        return {"status": "ERROR", "message": "No historical price data available."}

    df = history.copy()
    required_columns = ["High", "Low", "Close"]
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        return {"status": "ERROR", "message": f"Missing required column: {missing[0]}"}

    for column in required_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # Invalid/non-positive OHLC observations are not usable market evidence.
    # Drop them before ATR and structural calculations so corrupted candles
    # cannot manufacture support, resistance, or volatility levels.
    df = df.dropna(subset=required_columns)
    df = df[(df["High"] > 0) & (df["Low"] > 0) & (df["Close"] > 0) & (df["High"] >= df["Low"])]
    if len(df) < 20:
        return {"status": "ERROR", "message": "Insufficient valid historical data."}

    history_close = _safe_float(df["Close"].iloc[-1])
    if history_close is None or history_close <= 0:
        return {"status": "ERROR", "message": "Invalid current historical close."}

    # The historical close remains the basis for ATR/structure calculations.
    # When a symbol is known, use the canonical freshest market observation for
    # the displayed/current trading price so the trade plan cannot silently use
    # an older close when a newer provider observation exists.
    current_price = history_close
    market_observation = None
    price_source = "historical_close"
    quote_timestamp = None
    quote_frequency = "historical"
    is_intraday = False
    is_tick_live = False
    if symbol:
        normalized = symbol.strip().upper()
        if normalized:
            market_observation = get_latest_available_price(normalized)
            provider_price = _safe_float(market_observation.get("price"))
            if provider_price is not None and provider_price > 0:
                current_price = provider_price
                price_source = market_observation.get("source", "market_observation")
                quote_timestamp = market_observation.get("observed_at")
                quote_frequency = market_observation.get("frequency", "available")
                is_intraday = bool(market_observation.get("is_intraday", False))
                is_tick_live = bool(market_observation.get("is_tick_live", False))

    score = _safe_float(technical_score)
    if score is None:
        return {
            "status": "INSUFFICIENT DATA",
            "message": "Technical score is unavailable; trade plan cannot be generated safely.",
            "technical_score": None,
            "current_price": round(current_price, 2),
            "price_source": price_source,
            "quote_timestamp": quote_timestamp,
            "quote_frequency": quote_frequency,
            "is_intraday": is_intraday,
            "is_tick_live": is_tick_live,
        }
    score = _clamp(score, 0.0, 100.0)

    previous_close = df["Close"].shift(1)
    true_range = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - previous_close).abs(),
            (df["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = _safe_float(true_range.rolling(window=14, min_periods=14).mean().iloc[-1])
    if atr is None or atr <= 0:
        return {"status": "ERROR", "message": "Unable to calculate ATR."}

    atr_percent = atr / current_price * 100
    completed = df.iloc[:-1]
    if completed.empty:
        completed = df.copy()

    short_window = completed.tail(20)
    medium_window = completed.tail(50)
    support_20 = _safe_float(short_window["Low"].min())
    resistance_20 = _safe_float(short_window["High"].max())
    support_50 = _safe_float(medium_window["Low"].min())
    resistance_50 = _safe_float(medium_window["High"].max())

    support_20 = support_20 if support_20 is not None else current_price - 2 * atr
    resistance_20 = resistance_20 if resistance_20 is not None else current_price + 2 * atr
    support_50 = support_50 if support_50 is not None else support_20
    resistance_50 = resistance_50 if resistance_50 is not None else resistance_20

    close = df["Close"]
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    latest_ema20 = _safe_float(ema20.iloc[-1])
    latest_ema50 = _safe_float(ema50.iloc[-1])
    bullish_trend = (
        latest_ema20 is not None
        and latest_ema50 is not None
        and current_price > latest_ema20
        and latest_ema20 > latest_ema50
    )
    bearish_trend = (
        latest_ema20 is not None
        and latest_ema50 is not None
        and current_price < latest_ema20
        and latest_ema20 < latest_ema50
    )

    if score >= 80:
        signal, target_mult, stop_mult = "STRONG BUY", 3.0, 1.50
    elif score >= 65:
        signal, target_mult, stop_mult = "BUY", 2.5, 1.50
    elif score >= 50:
        signal, target_mult, stop_mult = "HOLD / WATCH", 2.0, 1.50
    elif score >= 35:
        signal, target_mult, stop_mult = "WEAK / CAUTIOUS", 1.5, 1.75
    else:
        signal, target_mult, stop_mult = "AVOID / SELL", 1.0, 2.0

    if bearish_trend:
        target_mult = max(0.75, target_mult - 0.25)
    elif bullish_trend:
        target_mult += 0.25

    minimum_risk_distance = atr * stop_mult
    atr_stop = current_price - minimum_risk_distance
    support_buffer = support_20 - 0.25 * atr
    distance_to_support = current_price - support_20
    if support_20 < current_price and distance_to_support <= 2.5 * atr:
        stop_loss = min(atr_stop, support_buffer)
    else:
        stop_loss = atr_stop
    stop_loss = max(stop_loss, 0.01)
    risk_per_share = current_price - stop_loss
    if risk_per_share <= 0:
        return {"status": "ERROR", "message": "Unable to determine valid stop loss."}

    volatility_target = current_price + atr * target_mult
    target_price = volatility_target
    resistance_distance = resistance_20 - current_price
    if resistance_20 > current_price and resistance_distance <= 3.0 * atr:
        if score < 50:
            target_price = min(volatility_target, resistance_20)
        else:
            target_price = max(volatility_target, min(resistance_20, current_price + 3.0 * atr))
    if target_price <= current_price:
        target_price = current_price + 0.75 * atr

    potential_reward = target_price - current_price
    risk_reward = potential_reward / risk_per_share
    upside_percent = potential_reward / current_price * 100
    stop_loss_percent = risk_per_share / current_price * 100

    if score < 35:
        setup_quality = "POOR"
    elif score < 50 or risk_reward < 1.0:
        setup_quality = "WEAK"
    elif score >= 65 and risk_reward >= 1.5 and bullish_trend:
        setup_quality = "STRONG"
    elif risk_reward >= 1.25:
        setup_quality = "ACCEPTABLE"
    else:
        setup_quality = "CAUTIOUS"

    trade_note = (
        "The displayed price is the freshest canonical market observation when available; "
        "ATR and structural levels remain calculated from historical data."
    )
    if score < 35:
        trade_note += " Technical conditions are weak; levels are risk-reference levels, not a long-entry recommendation."
    elif score < 50:
        trade_note += " Consider confirmation before treating the target as actionable."
    elif risk_reward < 1.0:
        trade_note += " Projected reward is smaller than estimated risk."

    result = {
        "status": "OK",
        "current_price": round(current_price, 2),
        "price_source": price_source,
        "quote_timestamp": quote_timestamp,
        "quote_frequency": quote_frequency,
        "is_intraday": is_intraday,
        "is_tick_live": is_tick_live,
        "target_price": round(target_price, 2),
        "stop_loss": round(stop_loss, 2),
        "upside_percent": round(upside_percent, 2),
        "risk_reward": round(risk_reward, 2),
        "atr": round(atr, 2),
        "support": round(support_20, 2),
        "resistance": round(resistance_20, 2),
        "technical_score": round(score, 2),
        "signal": signal,
        "setup_quality": setup_quality,
        "trade_note": trade_note,
        "atr_percent": round(atr_percent, 2),
        "stop_loss_percent": round(stop_loss_percent, 2),
        "risk_per_share": round(risk_per_share, 2),
        "support_20": round(support_20, 2),
        "resistance_20": round(resistance_20, 2),
        "support_50": round(support_50, 2),
        "resistance_50": round(resistance_50, 2),
        "bullish_trend": bullish_trend,
        "bearish_trend": bearish_trend,
    }
    if market_observation is not None:
        result["market_observation"] = market_observation
    return result
