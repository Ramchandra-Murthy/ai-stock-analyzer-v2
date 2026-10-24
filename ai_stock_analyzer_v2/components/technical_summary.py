import streamlit as st


def show_technical_summary(df):
    """
    Displays a technical summary of the latest indicators.
    """

    if df is None or df.empty:
        st.warning("No technical data available.")
        return

    latest = df.iloc[-1]

    price = latest["Close"]
    ema20 = latest["EMA20"]
    ema50 = latest["EMA50"]
    ema200 = latest["EMA200"]
    rsi = latest["RSI"]
    macd = latest["MACD"]
    signal = latest["MACD_Signal"]
    atr = latest["ATR"]
    support = latest["Support"]
    resistance = latest["Resistance"]

    # -------------------------------------------------------
    # Trend
    # -------------------------------------------------------

    if price > ema20 > ema50 > ema200:
        trend = "🟢 Strong Uptrend"

    elif price < ema20 < ema50 < ema200:
        trend = "🔴 Strong Downtrend"

    else:
        trend = "🟡 Sideways"

    # -------------------------------------------------------
    # RSI
    # -------------------------------------------------------

    if rsi >= 70:
        rsi_text = f"{rsi:.2f} (Overbought)"

    elif rsi <= 30:
        rsi_text = f"{rsi:.2f} (Oversold)"

    else:
        rsi_text = f"{rsi:.2f} (Neutral)"

    # -------------------------------------------------------
    # MACD
    # -------------------------------------------------------

    if macd > signal:
        macd_text = "🟢 Bullish"

    else:
        macd_text = "🔴 Bearish"

    # -------------------------------------------------------
    # Volume
    # -------------------------------------------------------

    if latest["Volume"] > latest["Volume_MA20"]:
        volume_text = "Above Average"

    else:
        volume_text = "Below Average"

    # -------------------------------------------------------
    # Recommendation
    # -------------------------------------------------------

    score = 0

    if price > ema20:
        score += 1

    if ema20 > ema50:
        score += 1

    if ema50 > ema200:
        score += 1

    if macd > signal:
        score += 1

    if 50 < rsi < 70:
        score += 1

    if score >= 4:
        recommendation = "🟢 BUY"

    elif score >= 2:
        recommendation = "🟡 HOLD"

    else:
        recommendation = "🔴 SELL"

    # -------------------------------------------------------
    # Display
    # -------------------------------------------------------

    st.subheader("📊 Technical Summary")

    c1, c2, c3 = st.columns(3)

    c1.metric("Trend", trend)
    c2.metric("RSI", rsi_text)
    c3.metric("MACD", macd_text)

    c1, c2, c3 = st.columns(3)

    c1.metric("ATR", f"{atr:.2f}")
    c2.metric("Support", f"₹{support:.2f}")
    c3.metric("Resistance", f"₹{resistance:.2f}")

    st.metric("Volume", volume_text)

    st.success(f"Recommendation : {recommendation}")
