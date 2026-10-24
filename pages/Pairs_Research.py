"""Pairs Research: cointegration scan and spread backtest (research only)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.pairs_trading import BANK_PAIRS, backtest_pair, scan_pairs
from services.cached_download import cached_download

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
def _closes(symbols: tuple[str, ...], period: str) -> pd.DataFrame:
    tickers = [f"{s}.NS" for s in symbols]
    raw = cached_download(tickers, period=period, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        return pd.DataFrame()
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    if not isinstance(raw.columns, pd.MultiIndex):
        close.columns = tickers[:1]
    close.columns = [str(c).removesuffix(".NS") for c in close.columns]
    return close


period = st.selectbox("History", ["5y", "10y"], index=0)
custom = st.text_input("Custom pair (two NSE symbols, optional)", "")
pairs = list(BANK_PAIRS)
if custom.strip():
    parts = custom.replace("/", " ").replace(",", " ").upper().split()
    if len(parts) == 2:
        pairs = [(parts[0], parts[1])]
    else:
        st.error("Enter exactly two symbols.")
        st.stop()
cost = st.number_input("Cost per trade, each side (bps of gross)", 0.0, 100.0, 10.0, 1.0)

if st.button("Scan and backtest", type="primary"):
    symbols = tuple(sorted({s for p in pairs for s in p}))
    prices = _closes(symbols, period)
    if prices.empty:
        st.error("No price data came back. Try again shortly.")
        st.stop()
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
