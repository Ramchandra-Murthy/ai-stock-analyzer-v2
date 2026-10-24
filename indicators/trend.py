def detect_trend(df):

    last = df.iloc[-1]

    sma20 = last["SMA_20"]
    sma50 = last["SMA_50"]
    ema20 = last["EMA_20"]

    if sma20 > sma50:
        trend = "Bullish"
    elif sma20 < sma50:
        trend = "Bearish"
    else:
        trend = "Sideways"

    if ema20 > sma20:
        momentum = "Strong"
    else:
        momentum = "Weak"

    return {"Trend": trend, "Momentum": momentum}
