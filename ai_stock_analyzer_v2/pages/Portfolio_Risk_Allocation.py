"""Streamlit page for NSE/BSE portfolio risk and allocation research."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.algorithmic_scanner import scan_universe
from algorithmic_trading.portfolio_allocation import (
    PortfolioLimits,
    allocate_scan,
)
from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES
from services.cached_download import cached_download

st.set_page_config(
    page_title="NSE/BSE Portfolio Risk",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ NSE/BSE Portfolio Risk & Allocation")
st.caption(
    "Portfolio-level controls based on gross/net exposure, concentration and "
    "transparent allocation baselines. Research only."
)

left, right = st.columns(2)
with left:
    exchange = st.selectbox("Exchange", ["NSE", "BSE"])
    universe = NSE_CANDIDATES if exchange == "NSE" else BSE_CANDIDATES
    count = st.slider(
        "Symbols to scan",
        min_value=10,
        max_value=min(30, len(universe)),
        value=10,
        step=5,
    )
    method = st.selectbox("Allocation method", ["equal", "inverse_volatility"])
with right:
    max_position = st.slider(
        "Maximum position weight",
        min_value=0.05,
        max_value=0.50,
        value=0.20,
        step=0.05,
    )
    max_positions = st.slider(
        "Maximum simultaneous positions",
        min_value=1,
        max_value=20,
        value=10,
    )
    max_gross = st.slider(
        "Maximum gross exposure",
        min_value=0.25,
        max_value=2.0,
        value=1.0,
        step=0.25,
    )
    max_net = st.slider(
        "Maximum net exposure",
        min_value=0.25,
        max_value=1.0,
        value=1.0,
        step=0.25,
    )

if st.button("Calculate portfolio allocation", type="primary"):
    symbols = universe[:count]

    with st.spinner(f"Scanning {count} {exchange} symbols..."):
        scan = scan_universe(
            symbols=symbols,
            exchange=exchange,
            capital=100_000.0,
            period="1y",
        )
        tickers = [f"{symbol}.NS" if exchange == "NSE" else f"{symbol}.BO" for symbol in symbols]
        history = cached_download(
            tickers=tickers,
            period="1y",
            auto_adjust=False,
            progress=False,
            group_by="ticker",
            threads=True,
        )

    if scan.empty or history.empty:
        st.warning("No usable data was returned for the selected universe.")
        st.stop()

    return_frames: dict[str, pd.Series] = {}
    for symbol in scan["symbol"]:
        ticker = f"{symbol}.NS" if exchange == "NSE" else f"{symbol}.BO"
        if isinstance(history.columns, pd.MultiIndex):
            if ticker not in history.columns.get_level_values(0):
                continue
            close = history[ticker]["Close"]
        else:
            close = history["Close"]
        return_frames[symbol] = pd.to_numeric(close, errors="coerce").pct_change()

    returns = pd.DataFrame(return_frames).dropna(how="all")

    limits = PortfolioLimits(
        max_gross_exposure=max_gross,
        max_net_exposure=max_net,
        max_position_weight=max_position,
        max_positions=max_positions,
    )
    allocation = allocate_scan(scan, returns, limits, method=method)

    if allocation.empty:
        st.info("No LONG or SHORT signals are eligible for allocation.")
        st.stop()

    gross = float(allocation["target_weight"].abs().sum())
    net = float(allocation["target_weight"].sum())

    cols = st.columns(4)
    cols[0].metric("Positions", len(allocation))
    cols[1].metric("Gross exposure", f"{gross:.1%}")
    cols[2].metric("Net exposure", f"{net:.1%}")
    cols[3].metric(
        "Largest position",
        f"{allocation['target_weight'].abs().max():.1%}",
    )

    st.subheader("Portfolio allocation")
    st.dataframe(
        allocation,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Allocation weights")
    st.bar_chart(allocation.set_index("symbol")["target_weight"])
