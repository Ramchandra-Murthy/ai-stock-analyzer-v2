"""Streamlit page for manual paper trading of NSE/BSE algorithmic signals."""

from __future__ import annotations

import streamlit as st

from algorithmic_trading.algorithmic_paper import rebalance_from_scan
from algorithmic_trading.algorithmic_scanner import scan_universe
from algorithmic_trading.paper_trading import PaperPortfolio
from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES

st.set_page_config(
    page_title="NSE/BSE Algorithmic Paper Trading",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 NSE/BSE Algorithmic Paper Trading")
st.caption(
    "Manual simulation only. Scanner decisions can be applied to an in-memory "
    "paper portfolio; no broker connection or live order is submitted."
)

if "paper_portfolio" not in st.session_state:
    st.session_state.paper_portfolio = PaperPortfolio(cash=100_000.0)

portfolio = st.session_state.paper_portfolio

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
with right:
    capital = st.number_input(
        "Scanner capital (₹)",
        min_value=1_000.0,
        value=portfolio.cash,
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
    period = st.selectbox("History", ["6mo", "1y", "2y"], index=1)

scan_button = st.button("Run algorithmic scan", type="primary")

if scan_button:
    with st.spinner(f"Scanning {count} {exchange} symbols..."):
        st.session_state.paper_scan = scan_universe(
            symbols=universe[:count],
            exchange=exchange,
            capital=capital,
            risk_fraction=risk_fraction,
            period=period,
        )

scan = st.session_state.get("paper_scan")

if scan is not None and not scan.empty:
    st.subheader("Current algorithmic signals")
    st.dataframe(scan, use_container_width=True, hide_index=True)

    if st.button("Apply signals to paper portfolio"):
        result = rebalance_from_scan(portfolio, scan)
        st.session_state.paper_rebalance = result
        st.success(f"Applied {len(result.fills)} simulated fills.")

    prices = {str(row["symbol"]): float(row["price"]) for _, row in scan.iterrows()}
    equity = portfolio.mark_to_market(prices)

    cols = st.columns(3)
    cols[0].metric("Cash", f"₹{portfolio.cash:,.2f}")
    cols[1].metric("Paper equity", f"₹{equity:,.2f}")
    cols[2].metric("Open positions", len(portfolio.positions))

    st.subheader("Positions")
    st.dataframe(
        [
            {"symbol": symbol, "quantity": quantity}
            for symbol, quantity in portfolio.positions.items()
        ],
        use_container_width=True,
        hide_index=True,
    )

    if portfolio.fills:
        st.subheader("Paper fills")
        st.dataframe(
            [
                {
                    "symbol": fill.symbol,
                    "quantity": fill.quantity,
                    "price": fill.price,
                    "side": fill.side,
                    "cost": fill.cost,
                }
                for fill in portfolio.fills
            ],
            use_container_width=True,
            hide_index=True,
        )
