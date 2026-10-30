"""Streamlit page for the NSE/BSE algorithmic research engine."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.pipeline import analyze_symbol
from components.disclaimer import show_disclaimer
from services.cached_download import cached_download

st.set_page_config(
    page_title="NSE/BSE Algorithmic Trading",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 NSE/BSE Algorithmic Trading")
show_disclaimer()
st.caption(
    "Research dashboard combining regime, relative strength, measured edge, "
    "signal composition and position sizing. It does not place live orders."
)

left, right = st.columns(2)
with left:
    exchange = st.selectbox("Exchange", ["NSE", "BSE"])
    symbol = st.text_input("Symbol", "RELIANCE").strip().upper()
    capital = st.number_input(
        "Research capital (₹)",
        min_value=1_000.0,
        value=100_000.0,
        step=10_000.0,
    )
with right:
    risk_fraction = st.number_input(
        "Risk fraction",
        min_value=0.001,
        max_value=0.10,
        value=0.01,
        step=0.001,
        format="%.3f",
    )
    period = st.selectbox("History", ["6mo", "1y", "2y", "5y"], index=1)
    run = st.button("Run algorithmic analysis", type="primary")

if run:
    ticker = f"{symbol}.NS" if exchange == "NSE" else f"{symbol}.BO"
    benchmark_ticker = "^NSEI" if exchange == "NSE" else "^BSESN"

    with st.spinner(f"Loading {ticker}..."):
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

    if frame.empty:
        st.error(f"No usable market data returned for {ticker}.")
        st.stop()

    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    if isinstance(benchmark.columns, pd.MultiIndex):
        benchmark.columns = benchmark.columns.get_level_values(0)

    if "Close" not in frame or "Close" not in benchmark:
        st.error("Market data did not contain a usable Close series.")
        st.stop()

    result = analyze_symbol(
        symbol=symbol,
        frame=frame,
        benchmark=benchmark["Close"],
        capital=capital,
        risk_fraction=risk_fraction,
    )

    metric_cols = st.columns(5)
    metric_cols[0].metric("Exchange", exchange)
    metric_cols[1].metric("Regime", result.regime)
    metric_cols[2].metric("Regime score", result.regime_score)
    metric_cols[3].metric(
        "Relative return",
        (f"{result.relative_return_pct:.2f}%" if result.relative_return_pct is not None else "—"),
    )
    metric_cols[4].metric("Signal", result.signal.direction)

    st.subheader("Signal")
    st.metric("Signal score", f"{result.signal.score:.1f}")
    for reason in result.signal.reasons:
        st.write(f"• {reason}")

    st.subheader("Position sizing")
    size_cols = st.columns(4)
    size_cols[0].metric("Quantity", result.position_size.quantity)
    size_cols[1].metric("Risk budget", f"₹{result.position_size.risk_budget:,.2f}")
    size_cols[2].metric("Risk/share", f"₹{result.position_size.risk_per_share:,.2f}")
    size_cols[3].metric("Method", result.position_size.method)

    st.subheader("Market data")
    st.line_chart(frame["Close"].tail(120))
