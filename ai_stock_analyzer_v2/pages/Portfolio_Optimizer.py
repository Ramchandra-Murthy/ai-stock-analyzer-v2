"""Portfolio Optimizer: weights by several methods, tested walk-forward, plus position sizing."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.portfolio_optimizer import (
    METHODS,
    optimise,
    portfolio_stats,
    walk_forward_weights,
)
from algorithmic_trading.risk_sizing import atr_stop, fractional_kelly, risk_based_quantity
from services.cached_download import cached_download

st.set_page_config(page_title="Portfolio Optimizer", page_icon="⚖️", layout="wide")
st.title("⚖️ Portfolio Optimizer")
st.warning(
    "RESEARCH ONLY — optimised weights are in-sample estimates and often disappoint out of "
    "sample; the walk-forward comparison below is the honest test. Not advice."
)


@st.cache_data(ttl=600, show_spinner=False)
def _returns(symbols: tuple[str, ...], period: str) -> pd.DataFrame:
    tickers = [f"{s}.NS" for s in symbols]
    raw = cached_download(tickers, period=period, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        return pd.DataFrame()
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    if not isinstance(raw.columns, pd.MultiIndex):
        close.columns = tickers[:1]
    close.columns = [str(c).removesuffix(".NS") for c in close.columns]
    return close.pct_change().dropna(how="all")


tab_opt, tab_size = st.tabs(["Optimise", "Position sizing"])
with tab_opt:
    text = st.text_input("NSE symbols (comma separated)", "RELIANCE,TCS,HDFCBANK,ITC,INFY,SBIN")
    period = st.selectbox("History", ["5y", "10y"], index=0)
    cap = st.slider("Maximum weight per stock", 0.1, 1.0, 0.4, 0.05)
    if st.button("Optimise", type="primary"):
        symbols = tuple(dict.fromkeys(s.strip().upper() for s in text.split(",") if s.strip()))
        rets = _returns(symbols, period).dropna()
        try:
            if rets.empty:
                raise ValueError("No price data came back. Try again shortly.")
            rows, curves = {}, {}
            for method in METHODS:
                w = optimise(
                    rets,
                    method,
                    max_weight=cap if "variance" in method or "Sharpe" in method else 1.0,
                )
                rows[method] = w
                curves[method] = (
                    1
                    + walk_forward_weights(
                        rets,
                        method,
                        max_weight=cap if "variance" in method or "Sharpe" in method else 1.0,
                    )
                ).cumprod()
        except ValueError as exc:
            st.error(str(exc))
            st.stop()
        st.markdown("**Weights fitted on all history**")
        st.dataframe(pd.DataFrame(rows).style.format("{:.1%}"), use_container_width=True)
        st.markdown(
            "**Out-of-sample growth of 1** (re-optimised every quarter on the prior 2 years)"
        )
        st.line_chart(pd.DataFrame(curves))
        summary = pd.DataFrame({m: portfolio_stats(rows[m], rets) for m in METHODS}).T
        st.markdown("**In-sample statistics**")
        st.dataframe(summary.style.format("{:.2f}"), use_container_width=True)

with tab_size:
    capital = st.number_input("Capital (₹)", 10_000.0, value=1_000_000.0, step=50_000.0)
    risk = st.slider("Risk per trade (% of capital)", 0.1, 5.0, 1.0, 0.1) / 100
    entry = st.number_input("Entry price", 0.01, value=2_500.0)
    atr = st.number_input("ATR (optional, sets the stop)", 0.0, value=40.0)
    mult = st.number_input("ATR multiple", 0.5, 6.0, 2.0, 0.5)
    lot = st.number_input("Lot size", 1, 10_000, 1)
    try:
        stop = atr_stop(entry, atr, mult) if atr > 0 else entry * 0.97
        size = risk_based_quantity(
            capital, risk, entry, stop, lot_size=int(lot), max_position_pct=0.25
        )
        st.metric("Quantity", f"{size['quantity']:,.0f}", f"stop {stop:,.2f}")
        st.caption(
            f"Notional ₹{size['notional']:,.0f}; loss at the stop about ₹{size['risk_amount']:,.0f} "
            f"({size['risk_pct_of_capital']:.2%}). Gaps can exceed the stop. Position capped at 25% of capital."
        )
    except ValueError as exc:
        st.error(str(exc))
    win = st.slider("Win rate", 0.1, 0.9, 0.5, 0.01)
    payoff = st.number_input("Average win / average loss", 0.1, 10.0, 1.5, 0.1)
    st.caption(
        f"Quarter-Kelly (capped at 25%): {fractional_kelly(win, payoff):.1%} of capital. "
        "Win rate and payoff are estimates, and full Kelly is far too aggressive when they are wrong."
    )
