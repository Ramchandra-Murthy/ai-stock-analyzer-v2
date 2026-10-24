import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_candlestick(df):
    """
    Professional TradingView-style chart with:
    - Candlesticks
    - EMA 20 / 50 / 200
    - Bollinger Bands
    - Support & Resistance
    - Volume
    """

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.75, 0.25],
    )

    # ======================================================
    # Candlestick
    # ======================================================

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
        ),
        row=1,
        col=1,
    )

    # ======================================================
    # EMA 20
    # ======================================================

    fig.add_trace(
        go.Scatter(x=df.index, y=df["EMA20"], mode="lines", name="EMA 20", line={"width": 1.5}),
        row=1,
        col=1,
    )

    # ======================================================
    # EMA 50
    # ======================================================

    fig.add_trace(
        go.Scatter(x=df.index, y=df["EMA50"], mode="lines", name="EMA 50", line={"width": 1.5}),
        row=1,
        col=1,
    )

    # ======================================================
    # EMA 200
    # ======================================================

    fig.add_trace(
        go.Scatter(x=df.index, y=df["EMA200"], mode="lines", name="EMA 200", line={"width": 2}),
        row=1,
        col=1,
    )

    # ======================================================
    # Bollinger Bands
    # ======================================================

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["BB_Upper"],
            mode="lines",
            name="BB Upper",
            line={"dash": "dot"},
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["BB_Lower"],
            mode="lines",
            name="BB Lower",
            line={"dash": "dot"},
        ),
        row=1,
        col=1,
    )

    # ======================================================
    # Support
    # ======================================================

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Support"],
            mode="lines",
            name="Support",
            line={"dash": "dash"},
        ),
        row=1,
        col=1,
    )

    # ======================================================
    # Resistance
    # ======================================================

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Resistance"],
            mode="lines",
            name="Resistance",
            line={"dash": "dash"},
        ),
        row=1,
        col=1,
    )

    # ======================================================
    # Volume
    # ======================================================

    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume"), row=2, col=1)

    # ======================================================
    # Layout
    # ======================================================

    fig.update_layout(
        title="Technical Price Chart",
        template="plotly_white",
        height=850,
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        legend={"orientation": "h", "y": 1.02, "x": 0},
    )

    fig.update_yaxes(title_text="Price (₹)", row=1, col=1)

    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig
