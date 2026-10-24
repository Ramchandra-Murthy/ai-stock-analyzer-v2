"""Streamlit page for multi-symbol NSE/BSE algorithmic research."""

from __future__ import annotations

import streamlit as st

from algorithmic_trading.algorithmic_scanner import scan_universe
from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES

st.set_page_config(
    page_title="NSE/BSE Algorithmic Scanner",
    page_icon="📊",
    layout="wide",
)

st.title("📊 NSE/BSE Algorithmic Opportunity Scanner")
st.caption(
    "Ranks the selected research universe using the integrated regime, "
    "relative-strength, signal and position-sizing pipeline. Research only."
)

left, right = st.columns(2)
with left:
    exchange = st.selectbox("Exchange", ["NSE", "BSE"])
    universe = NSE_CANDIDATES if exchange == "NSE" else BSE_CANDIDATES
    count = st.slider(
        "Symbols to scan",
        min_value=10,
        max_value=min(50, len(universe)),
        value=20,
        step=5,
    )
with right:
    capital = st.number_input(
        "Research capital (₹)",
        min_value=1_000.0,
        value=100_000.0,
        step=10_000.0,
    )
    risk_fraction = st.number_input(
        "Risk fraction",
        min_value=0.001,
        max_value=0.10,
        value=0.01,
        step=0.001,
        format="%.3f",
    )
    period = st.selectbox("History", ["6mo", "1y", "2y", "5y"], index=1)

run = st.button("Scan NSE/BSE universe", type="primary")

if run:
    symbols = universe[:count]
    with st.spinner(f"Scanning {len(symbols)} {exchange} symbols..."):
        result = scan_universe(
            symbols=symbols,
            exchange=exchange,
            capital=capital,
            risk_fraction=risk_fraction,
            period=period,
        )

    if result.empty:
        st.warning("No usable market data was returned for the selected universe.")
        st.stop()

    st.success(f"Scanned {len(result)} symbols.")

    top = result.head(10)
    st.subheader("Top 10 by algorithmic signal score")
    st.dataframe(
        top[
            [
                "symbol",
                "price",
                "regime",
                "regime_score",
                "relative_return_pct",
                "signal",
                "signal_score",
                "quantity",
                "risk_budget",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Full scan")
    st.dataframe(result, use_container_width=True, hide_index=True)

    st.subheader("Signal distribution")
    st.bar_chart(result["signal"].value_counts())

    st.subheader("Signal score")
    st.bar_chart(result.set_index("symbol")["signal_score"])
