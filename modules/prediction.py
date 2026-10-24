import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.technical_service import get_price_history

# ==========================================================
# Download Stock Data
# ==========================================================


def download_stock(symbol):
    """Use the canonical technical-data service for historical prices."""
    try:
        return get_price_history(symbol, period="1y")
    except Exception as e:
        st.exception(e)
        return None


# ==========================================================
# Prediction Model
# ==========================================================


def predict_prices(df, days=30):
    """
    Deterministic technical trend forecast.

    Combines recent log-return momentum, EMA20/EMA50 trend direction,
    and volatility damping. It is deliberately not labelled as an AI/ML
    model because this module does not train or load a machine-learning model.
    """
    if df is None or df.empty or "Close" not in df.columns:
        return []

    try:
        days = int(days)
    except (TypeError, ValueError):
        return []

    if days <= 0:
        return []

    close = pd.to_numeric(df["Close"], errors="coerce").dropna()
    if len(close) < 20:
        return []

    last_price = float(close.iloc[-1])
    if last_price <= 0:
        return []

    log_returns = (
        (close / close.shift(1))
        .apply(lambda x: __import__("math").log(x) if x > 0 else float("nan"))
        .dropna()
    )

    recent_momentum = float(log_returns.tail(10).mean())

    ema20 = (
        float(df["EMA20"].iloc[-1])
        if "EMA20" in df
        else float(close.ewm(span=20, adjust=False).mean().iloc[-1])
    )
    ema50 = (
        float(df["EMA50"].iloc[-1])
        if "EMA50" in df
        else float(close.ewm(span=50, adjust=False).mean().iloc[-1])
    )

    trend_strength = ((ema20 - ema50) / last_price) if ema20 > 0 and ema50 > 0 else 0.0

    volatility = float(log_returns.tail(20).std())
    if pd.isna(volatility):
        volatility = 0.0

    raw_daily_drift = (0.65 * recent_momentum) + (0.35 * trend_strength / 20.0)
    damping = 1.0 / (1.0 + 8.0 * max(volatility, 0.0))
    daily_drift = max(-0.02, min(0.02, raw_daily_drift * damping))

    forecast = []
    price = last_price

    for step in range(1, days + 1):
        horizon_drift = daily_drift * (0.97 ** (step - 1))
        price *= float(__import__("math").exp(horizon_drift))
        forecast.append(round(price, 2))

    return forecast


# ==========================================================
# Prediction Page
# ==========================================================


def show():

    st.title("📈 Stock Price Trend Forecast")

    st.write(
        "Deterministic technical trend forecast using momentum, EMA trend, and volatility damping."
    )

    symbol = st.text_input("Stock Symbol", value="RELIANCE.NS")

    forecast_days = st.slider("Forecast Days", 5, 60, 30)

    if st.button("Predict"):

        with st.spinner("Downloading market data..."):

            df = download_stock(symbol)

        if df is None:

            st.error(f"Unable to download data for {symbol}")

            return

        st.success("Market data downloaded successfully.")

        st.subheader("Latest Market Data")

        st.dataframe(df.tail(), use_container_width=True)

        prediction = predict_prices(df, forecast_days)

        if not prediction:
            st.error("Insufficient valid price history to calculate a trend forecast.")
            return

        current_price = float(df["Close"].iloc[-1])

        predicted_price = prediction[-1]

        expected_return = ((predicted_price - current_price) / current_price) * 100

        st.divider()

        c1, c2, c3 = st.columns(3)

        c1.metric("Current Price", f"₹{current_price:,.2f}")

        c2.metric("Predicted Price", f"₹{predicted_price:,.2f}")

        c3.metric("Expected Return", f"{expected_return:.2f}%")

        st.divider()

        fig = go.Figure()

        fig.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines", name="Historical Price"))

        future_dates = pd.date_range(start=df.index[-1], periods=forecast_days + 1, freq="B")[1:]

        fig.add_trace(
            go.Scatter(x=future_dates, y=prediction, mode="lines+markers", name="Trend Forecast")
        )

        fig.update_layout(
            title=f"{symbol} Technical Trend Forecast",
            xaxis_title="Date",
            yaxis_title="Price",
            height=600,
            template="plotly_white",
        )

        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        if expected_return > 10:

            st.success("🟢 Strong Bullish Outlook")

        elif expected_return > 3:

            st.info("🟡 Bullish Outlook")

        elif expected_return > -3:

            st.warning("🟠 Sideways Outlook")

        else:

            st.error("🔴 Bearish Outlook")

        st.divider()

        st.subheader("Prediction Summary")

        summary = pd.DataFrame(
            {
                "Metric": [
                    "Stock",
                    "Forecast",
                    "Current Price",
                    "Predicted Price",
                    "Expected Return",
                ],
                "Value": [
                    symbol,
                    f"{forecast_days} Days",
                    f"₹{current_price:.2f}",
                    f"₹{predicted_price:.2f}",
                    f"{expected_return:.2f}%",
                ],
            }
        )

        st.table(summary)

        st.info(
            "This is an educational technical trend forecast, not a guaranteed prediction or investment advice."
        )
