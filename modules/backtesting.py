import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.technical_service import get_price_history


def _run_backtest(history, initial_capital, cost_bps):
    """Backtest an EMA20/EMA50 crossover without using same-day signals."""
    if history is None or history.empty:
        raise ValueError("Historical price data is unavailable.")

    data = history.copy()

    required = {"Close", "EMA20", "EMA50"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(
            "Historical data is missing required columns: " + ", ".join(sorted(missing))
        )

    data = data.dropna(subset=["Close", "EMA20", "EMA50"]).copy()
    data = data[data["Close"] > 0]

    if len(data) < 2:
        raise ValueError("Not enough valid price history to run a backtest.")

    # Today's EMA values determine the position for the next trading bar.
    data["signal"] = (data["EMA20"] > data["EMA50"]).astype(int)
    data["position"] = data["signal"].shift(1).fillna(0)

    data["market_return"] = data["Close"].pct_change().fillna(0)
    data["turnover"] = data["position"].diff().abs()
    data["turnover"] = data["turnover"].fillna(data["position"].abs())

    transaction_cost = cost_bps / 10_000
    data["strategy_return"] = (
        data["position"] * data["market_return"] - data["turnover"] * transaction_cost
    )

    data["strategy_equity"] = initial_capital * (1 + data["strategy_return"]).cumprod()
    data["buy_hold_equity"] = initial_capital * (1 + data["market_return"]).cumprod()

    peak = data["strategy_equity"].cummax()
    data["drawdown"] = data["strategy_equity"] / peak - 1

    elapsed_days = (data.index[-1] - data.index[0]).days
    total_return = data["strategy_equity"].iloc[-1] / initial_capital - 1

    if elapsed_days > 0 and data["strategy_equity"].iloc[-1] > 0:
        cagr = (data["strategy_equity"].iloc[-1] / initial_capital) ** (365.25 / elapsed_days) - 1
    else:
        cagr = float("nan")

    metrics = {
        "total_return": total_return,
        "cagr": cagr,
        "max_drawdown": data["drawdown"].min(),
        "buy_hold_return": (data["buy_hold_equity"].iloc[-1] / initial_capital - 1),
        "trade_count": int((data["position"].diff().fillna(data["position"]) > 0).sum()),
    }

    equity_columns = ["strategy_equity", "buy_hold_equity"]
    equity = data[equity_columns].apply(pd.to_numeric, errors="coerce")
    if equity.empty or not equity.index.is_monotonic_increasing:
        raise ValueError("Backtest equity series is invalid.")
    if not equity.index.is_unique:
        raise ValueError("Backtest dates contain duplicates.")
    if not equity.notna().any(axis=None):
        raise ValueError("Backtest equity series contains no valid values.")

    return data, metrics


def show():
    st.title("📉 Backtesting")
    st.caption("Historical EMA crossover strategy simulation")

    st.info(
        "This is a historical simulation, not a prediction or investment "
        "recommendation. Results exclude taxes and brokerage beyond the "
        "transaction-cost assumption below."
    )

    with st.form("backtesting_form"):
        symbol = (
            st.text_input(
                "NSE symbol",
                value="RELIANCE",
                key="backtesting_symbol",
            )
            .strip()
            .upper()
        )

        period = st.selectbox(
            "Historical period",
            ["1y", "2y", "5y", "10y"],
            index=0,
            key="backtesting_period",
        )

        col1, col2 = st.columns(2)

        with col1:
            initial_capital = st.number_input(
                "Starting capital (₹)",
                min_value=1_000,
                max_value=100_000_000,
                value=100_000,
                step=10_000,
            )

        with col2:
            cost_bps = st.number_input(
                "Estimated cost per position change (basis points)",
                min_value=0,
                max_value=500,
                value=10,
                step=5,
                help="10 basis points = 0.10% per entry or exit.",
            )

        submitted = st.form_submit_button(
            "Run backtest",
            use_container_width=True,
        )

    if not submitted:
        st.caption("Enter a symbol and select Run backtest to begin.")
        return

    if not symbol:
        st.warning("Please enter an NSE symbol.")
        return

    try:
        with st.spinner(f"Loading historical prices for {symbol}…"):
            history = get_price_history(symbol, period=period)

        results, metrics = _run_backtest(
            history,
            initial_capital=float(initial_capital),
            cost_bps=float(cost_bps),
        )
    except Exception as error:
        st.error(f"Backtest could not be completed: {error}")
        return

    st.subheader(f"{symbol} — {period} backtest")
    st.caption(
        "Strategy: EMA20 above EMA50 = hold; otherwise stay in cash. "
        "Signals are applied from the following bar."
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Strategy return", f"{metrics['total_return']:.2%}")
    m2.metric("Buy & hold return", f"{metrics['buy_hold_return']:.2%}")
    m3.metric("Max drawdown", f"{metrics['max_drawdown']:.2%}")

    m4, m5 = st.columns(2)
    m4.metric(
        "Annualized return (CAGR)",
        "N/A" if pd.isna(metrics["cagr"]) else f"{metrics['cagr']:.2%}",
    )
    m5.metric("Entries", metrics["trade_count"])

    st.subheader("Portfolio value")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=results.index,
            y=results["buy_hold_equity"],
            mode="lines",
            name="Buy & hold",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=results.index,
            y=results["strategy_equity"],
            mode="lines",
            name="EMA strategy",
        )
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Portfolio value (₹)",
        yaxis={"rangemode": "tozero"},
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Recent backtest data")
    display_columns = [
        "Close",
        "EMA20",
        "EMA50",
        "position",
        "strategy_equity",
        "buy_hold_equity",
        "drawdown",
    ]

    recent_results = results[display_columns].tail(20).sort_index(ascending=False)
    st.dataframe(
        recent_results,
        use_container_width=True,
    )
