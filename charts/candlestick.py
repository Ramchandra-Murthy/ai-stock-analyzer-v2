import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_candlestick(df, symbol):

    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.55, 0.15, 0.15, 0.15],
        subplot_titles=(f"{symbol} Price", "Volume", "RSI", "MACD"),
    )

    # ==========================
    # Candlestick
    # ==========================

    fig.add_trace(
        go.Candlestick(
            x=df["Date"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
        ),
        row=1,
        col=1,
    )

    # ==========================
    # SMA 20
    # ==========================

    if "SMA_20" in df.columns:
        fig.add_trace(
            go.Scatter(x=df["Date"], y=df["SMA_20"], name="SMA 20", line={"width": 2}),
            row=1,
            col=1,
        )

    # ==========================
    # SMA 50
    # ==========================

    if "SMA_50" in df.columns:
        fig.add_trace(
            go.Scatter(x=df["Date"], y=df["SMA_50"], name="SMA 50", line={"width": 2}),
            row=1,
            col=1,
        )

    # ==========================
    # EMA 20
    # ==========================

    if "EMA_20" in df.columns:
        fig.add_trace(
            go.Scatter(x=df["Date"], y=df["EMA_20"], name="EMA 20", line={"width": 2}),
            row=1,
            col=1,
        )

    # ==========================
    # Bollinger Bands
    # ==========================

    if "BB_Upper" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["Date"],
                y=df["BB_Upper"],
                name="BB Upper",
                line={"width": 1, "dash": "dot"},
            ),
            row=1,
            col=1,
        )

    if "BB_Middle" in df.columns:
        fig.add_trace(
            go.Scatter(x=df["Date"], y=df["BB_Middle"], name="BB Middle", line={"width": 1}),
            row=1,
            col=1,
        )

    if "BB_Lower" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["Date"],
                y=df["BB_Lower"],
                name="BB Lower",
                line={"width": 1, "dash": "dot"},
            ),
            row=1,
            col=1,
        )

    # ==========================
    # Current Price
    # ==========================

    current_price = df["Close"].iloc[-1]

    fig.add_hline(
        y=current_price,
        row=1,
        col=1,
        line_dash="dot",
        annotation_text=f"Price {current_price:.2f}",
    )

    # ==========================
    # Support & Resistance
    # ==========================

    if "Support" in df.columns:
        fig.add_hline(
            y=df["Support"].iloc[-1],
            row=1,
            col=1,
            line_dash="dash",
            annotation_text="Support",
        )

    if "Resistance" in df.columns:
        fig.add_hline(
            y=df["Resistance"].iloc[-1],
            row=1,
            col=1,
            line_dash="dash",
            annotation_text="Resistance",
        )

    # ==========================
    # Volume
    # ==========================

    fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], name="Volume"), row=2, col=1)

    # ==========================
    # RSI
    # ==========================

    if "RSI_14" in df.columns:
        fig.add_trace(go.Scatter(x=df["Date"], y=df["RSI_14"], name="RSI"), row=3, col=1)

    fig.add_hline(y=70, row=3, col=1, line_dash="dash", annotation_text="70")

    fig.add_hline(y=30, row=3, col=1, line_dash="dash", annotation_text="30")

    # ==========================
    # MACD Histogram
    # ==========================

    if "Histogram" in df.columns:
        fig.add_trace(go.Bar(x=df["Date"], y=df["Histogram"], name="Histogram"), row=4, col=1)

    # ==========================
    # MACD
    # ==========================

    if "MACD" in df.columns:
        fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD"), row=4, col=1)

    if "Signal" in df.columns:
        fig.add_trace(go.Scatter(x=df["Date"], y=df["Signal"], name="Signal"), row=4, col=1)

    # ==========================
    # Layout
    # ==========================

    fig.update_layout(
        title=f"{symbol} Technical Dashboard",
        height=1200,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend_orientation="h",
        template="plotly_dark",
    )

    return fig
