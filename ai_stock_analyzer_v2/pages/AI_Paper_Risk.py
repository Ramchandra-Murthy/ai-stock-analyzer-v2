"""Streamlit dashboard for AI paper-trading risk controls."""

from __future__ import annotations

import streamlit as st

from ai_trading.risk import RiskLimits, risk_warnings

st.set_page_config(
    page_title="AI Paper Risk",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ AI Paper Trading Risk")
st.caption("Portfolio-level risk limits for the in-memory AI paper-trading session.")

portfolio = st.session_state.get("ai_paper_portfolio")
prices = st.session_state.get("ai_paper_prices", {})

if portfolio is None:
    st.info("Run the AI Paper Trading page first to create a paper portfolio.")
    st.stop()

max_exposure_pct = st.slider("Maximum portfolio exposure", 20.0, 100.0, 80.0, 5.0)
max_position_pct = st.slider("Maximum position size", 5.0, 50.0, 20.0, 5.0)
cash_reserve_pct = st.slider("Minimum cash reserve", 0.0, 50.0, 10.0, 5.0)

limits = RiskLimits(
    max_exposure_pct=max_exposure_pct,
    max_position_pct=max_position_pct,
    cash_reserve_pct=cash_reserve_pct,
)

equity = portfolio.equity(prices)
market_value = sum(
    quantity * float(prices[symbol])
    for symbol, quantity in portfolio.positions.items()
    if symbol in prices
)
exposure_pct = market_value / equity * 100.0 if equity > 0 else 0.0
cash_pct = portfolio.cash / equity * 100.0 if equity > 0 else 0.0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Portfolio equity", f"₹{equity:,.2f}")
m2.metric("Market exposure", f"{exposure_pct:.1f}%")
m3.metric("Cash reserve", f"{cash_pct:.1f}%")
m4.metric("Open positions", len(portfolio.positions))

warnings = risk_warnings(equity, portfolio.cash, market_value, limits)
if warnings:
    for warning in warnings:
        st.warning(warning)
else:
    st.success("Current portfolio is within the configured risk limits.")

st.subheader("Configured limits")
st.dataframe(
    [
        {"limit": "Maximum exposure", "value": f"{limits.max_exposure_pct:.1f}%"},
        {"limit": "Maximum position", "value": f"{limits.max_position_pct:.1f}%"},
        {"limit": "Minimum cash reserve", "value": f"{limits.cash_reserve_pct:.1f}%"},
    ],
    use_container_width=True,
    hide_index=True,
)

st.subheader("Open-position exposure")
if portfolio.positions:
    rows = []
    for symbol, quantity in portfolio.positions.items():
        price = prices.get(symbol)
        value = quantity * float(price) if price is not None else 0.0
        position_pct = value / equity * 100.0 if equity > 0 else 0.0
        rows.append(
            {
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "market_value": value,
                "portfolio_pct": position_pct,
                "within_position_limit": position_pct <= limits.max_position_pct,
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
else:
    st.info("No open paper positions.")
