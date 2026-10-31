"""Streamlit page for historical testing of the NSE/BSE algorithmic pipeline."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.signal_backtest import backtest_pipeline
from components.disclaimer import show_disclaimer
from services.cached_download import cached_download

st.set_page_config(
    page_title="NSE/BSE Algorithmic Backtest",
    page_icon="📈",
    layout="wide",
)

st.title("📈 NSE/BSE Algorithmic Backtest")
show_disclaimer()
st.caption(
    "Tests the same regime and relative-strength signal used by the algorithmic "
    "scanner. Historical results are research results, not future-return forecasts."
)

left, right = st.columns(2)
with left:
    exchange = st.selectbox("Exchange", ["NSE", "BSE"])
    symbol = st.text_input("Symbol", "RELIANCE").strip().upper()
    period = st.selectbox("History", ["2y", "5y", "10y"], index=0)
with right:
    capital = st.number_input(
        "Initial capital (₹)",
        min_value=1_000.0,
        value=100_000.0,
        step=10_000.0,
    )
    cost_bps = st.number_input(
        "Transaction cost (bps)",
        min_value=0.0,
        max_value=500.0,
        value=10.0,
        step=1.0,
    )
    run = st.button("Run backtest", type="primary")

if run:
    ticker = f"{symbol}.NS" if exchange == "NSE" else f"{symbol}.BO"
    benchmark_ticker = "^NSEI" if exchange == "NSE" else "^BSESN"

    with st.spinner(f"Loading {ticker} and {benchmark_ticker}..."):
        frame = cached_download(
            ticker,
            period=period,
            auto_adjust=False,
            progress=False,
        )
        benchmark = cached_download(
            benchmark_ticker,
            period=period,
            auto_adjust=False,
            progress=False,
        )

    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    if isinstance(benchmark.columns, pd.MultiIndex):
        benchmark.columns = benchmark.columns.get_level_values(0)

    if frame.empty or benchmark.empty:
        st.error("No usable historical market data was returned.")
        st.stop()

    if "Close" not in frame.columns or "Close" not in benchmark.columns:
        st.error("Historical data did not contain a usable Close series.")
        st.stop()

    try:
        data, metrics = backtest_pipeline(
            frame=frame,
            benchmark=benchmark["Close"],
            initial_capital=capital,
            cost_bps=cost_bps,
        )
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    cols = st.columns(6)
    cols[0].metric("Total return", f"{metrics.total_return:.2%}")
    cols[1].metric(
        "CAGR",
        f"{metrics.cagr:.2%}" if metrics.cagr is not None else "—",
    )
    cols[2].metric("Max drawdown", f"{metrics.max_drawdown:.2%}")
    cols[3].metric("Buy & hold", f"{metrics.buy_hold_return:.2%}")
    cols[4].metric("Trades", metrics.trade_count)
    cols[5].metric("Win rate", f"{metrics.win_rate:.2%}")

    st.subheader("Equity curve")
    st.line_chart(data[["strategy_equity", "buy_hold_equity"]])

    st.subheader("Drawdown")
    st.line_chart(data["drawdown"])

    st.subheader("Backtest data")
    st.dataframe(
        data.tail(250),
        use_container_width=True,
    )
