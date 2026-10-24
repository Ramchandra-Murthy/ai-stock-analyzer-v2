"""Momentum Portfolio: rank a universe by momentum, hold the leaders, rebalance monthly."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.momentum_portfolio import WEIGHTINGS, run_momentum_portfolio
from algorithmic_trading.regime_filter import trend_gate
from algorithmic_trading.trading_costs import RATES_VERIFIED, india_cost_model
from scanner.universe import NSE_CANDIDATES
from services.cached_download import cached_download

st.set_page_config(page_title="Momentum Portfolio", page_icon="🚀", layout="wide")
st.title("🚀 Momentum Portfolio")
st.warning(
    "RESEARCH ONLY — a historical backtest, not a forecast or advice. No orders are placed. "
    "The universe is today's list of large names, so results carry survivorship bias and "
    "flatter the strategy."
)
st.caption(
    "Each month: rank by 12-month return (skipping the latest month), hold the top N, and go "
    "to cash if nothing is rising. Decisions use the close and trade the next bar."
)


@st.cache_data(ttl=600, show_spinner=False)
def _load(symbols: tuple[str, ...], period: str) -> pd.DataFrame:
    tickers = [f"{s}.NS" for s in symbols]
    raw = cached_download(tickers, period=period, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        return pd.DataFrame()
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    if not isinstance(raw.columns, pd.MultiIndex):
        close.columns = tickers[:1]
    close.columns = [str(c).removesuffix(".NS") for c in close.columns]
    return close.dropna(how="all")


left, right = st.columns(2)
with left:
    count = st.slider("Universe size (first N of the NSE list)", 10, len(NSE_CANDIDATES), 30)
    period = st.selectbox("History", ["5y", "10y"], index=0)
    top_n = st.slider("Holdings", 1, 15, 5)
    weighting = st.radio("Weighting", WEIGHTINGS)
with right:
    lookback = st.number_input("Momentum lookback (days)", 60, 500, 252, 21)
    skip = st.number_input("Skip latest (days)", 0, 60, 21, 1)
    every = st.number_input("Rebalance every (days)", 5, 126, 21, 1)
    nse_costs = st.checkbox("NSE delivery costs + 5 bps slippage", value=True, help=RATES_VERIFIED)
    market_gate = st.checkbox(
        "Go to cash when the equal-weight universe is below its 200-day average"
    )

if st.button("Run backtest", type="primary"):
    symbols = tuple(NSE_CANDIDATES[:count])
    with st.spinner("Downloading prices..."):
        prices = _load(symbols, period)
    if prices.empty:
        st.error("No price data came back. Check your network or try again shortly.")
        st.stop()
    gate = None
    if market_gate:
        gate = trend_gate((prices.pct_change().mean(axis=1).fillna(0) + 1).cumprod(), 50, 200)
    try:
        result, bench = run_momentum_portfolio(
            prices,
            top_n=int(top_n),
            lookback=int(lookback),
            skip=int(skip),
            rebalance_every=int(every),
            weighting=weighting,
            cost_model=india_cost_model("delivery", slippage_bps=5.0) if nse_costs else None,
            gate=gate,
        )
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    cols = st.columns(4)
    cols[0].metric(
        "Return",
        f"{result.metrics['total_return']:.1%}",
        f"equal-weight {bench.metrics['total_return']:.1%}",
    )
    cols[1].metric("CAGR", f"{result.metrics['cagr']:.1%}", f"{bench.metrics['cagr']:.1%}")
    cols[2].metric("Sharpe", f"{result.metrics['sharpe']:.2f}", f"{bench.metrics['sharpe']:.2f}")
    cols[3].metric(
        "Max drawdown",
        f"{result.metrics['max_drawdown']:.1%}",
        f"{bench.metrics['max_drawdown']:.1%}",
    )
    st.line_chart(pd.DataFrame({"Momentum": result.equity, "Equal-weight universe": bench.equity}))
    st.caption(f"Average yearly one-way turnover: {result.turnover.mean() * 252:.0%} of equity.")
    st.markdown("**Latest holdings**")
    st.dataframe(result.rebalances.tail(12), hide_index=True, use_container_width=True)
