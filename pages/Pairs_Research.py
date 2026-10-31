"""Pairs Research: cointegration scan and spread backtest (research only)."""

from __future__ import annotations

import streamlit as st

from algorithmic_trading.pairs_trading import BANK_PAIRS, backtest_pair, scan_pairs
from services.price_table import load_close_prices
from services.symbol_resolver import company_label, resolve_symbol

st.set_page_config(page_title="Pairs Research", page_icon="🔗", layout="wide")
st.title("🔗 Pairs Research")
st.warning(
    "RESEARCH ONLY — one leg of a pair is a short position, which retail investors cannot hold "
    "in the cash market (futures or intraday only). Relationships break. No orders are placed."
)
st.caption(
    "The hedge ratio and cointegration test use only the first part of history; trading is "
    "simulated on the rest with the hedge ratio frozen."
)


@st.cache_data(ttl=600, show_spinner=False)
def _closes(items: tuple[tuple[str, str], ...], period: str):
    return load_close_prices(dict(items), period)


period = st.selectbox("History", ["5y", "10y"], index=0)
exchange = st.selectbox("Exchange for plain names in a custom pair", ["NSE", "BSE"])
custom = st.text_input(
    "Custom pair (two symbols, optional): `TCS INFY`, `NSE:TCS BSE:500209`, `500325.BO 532540.BO`",
    "",
)
legs: dict[str, str] = {}  # label -> Yahoo ticker


def _leg(raw: str, default: str) -> str:
    ticker = resolve_symbol(raw, default).ticker
    label = company_label(ticker)
    legs[label] = ticker
    return label


pairs: list[tuple[str, str]] = []
try:
    if custom.strip():
        parts = custom.replace("/", " ").replace(",", " ").split()
        if len(parts) != 2:
            raise ValueError("Enter exactly two symbols.")
        pairs = [(_leg(parts[0], exchange), _leg(parts[1], exchange))]
    else:
        pairs = [(_leg(a, "NSE"), _leg(b, "NSE")) for a, b in BANK_PAIRS]
    if len({legs[x] for pair in pairs for x in pair}) < 2:
        raise ValueError("The two legs of a pair must be different securities.")
except ValueError as exc:
    st.error(str(exc))
    st.stop()
cost = st.number_input("Cost per trade, each side (bps of gross)", 0.0, 100.0, 10.0, 1.0)

if st.button("Scan and backtest", type="primary"):
    wanted = sorted({s for p in pairs for s in p})
    prices, missing = _closes(tuple((name, legs[name]) for name in wanted), period)
    if prices.empty:
        st.error("No price data came back. Try again shortly.")
        st.stop()
    if missing:
        st.warning(f"No price history for {', '.join(missing)}; pairs using them are skipped.")
    pairs = [p for p in pairs if all(name in prices.columns for name in p)]
    table = scan_pairs(prices, pairs)
    if table.empty:
        st.info("None of these pairs had enough data.")
        st.stop()
    st.markdown("**Cointegration on the formation window** (more negative ADF = stronger)")
    st.dataframe(table, hide_index=True, use_container_width=True)
    st.caption(
        "5% critical value ≈ -3.34 (Engle-Granger, MacKinnon). Testing many pairs makes some pass by luck."
    )
    choice = st.selectbox("Backtest pair", list(table["pair"]))
    a, b = (s.strip() for s in choice.split("/"))
    try:
        res = backtest_pair(prices[a], prices[b], cost_bps=float(cost))
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    cols = st.columns(4)
    cols[0].metric("Out-of-sample return", f"{res.metrics['total_return']:.1%}")
    cols[1].metric("Sharpe", f"{res.metrics['sharpe']:.2f}")
    cols[2].metric("Max drawdown", f"{res.metrics['max_drawdown']:.1%}")
    cols[3].metric("Trades", res.trades)
    if not res.formation.cointegrated_5pct:
        st.warning("This pair did NOT pass the 5% cointegration test on the formation window.")
    st.line_chart(res.equity)
    st.markdown("**Spread z-score**")
    st.line_chart(res.zscore)
