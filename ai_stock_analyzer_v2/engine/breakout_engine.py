def detect_breakout(df):

    last = df.iloc[-1]

    signal = "NONE"

    reason = "Price is inside the trading range."

    if last["Close"] > last["Resistance"]:
        signal = "BREAKOUT"
        reason = "Close is above Resistance."

    elif last["Close"] < last["Support"]:
        signal = "BREAKDOWN"
        reason = "Close is below Support."

    return {"Signal": signal, "Reason": reason}
