"""Portfolio Optimizer: weights by several methods, tested walk-forward, plus position sizing."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.lab_inputs import parse_holdings, resolve_holdings
from algorithmic_trading.portfolio_optimizer import (
    METHODS,
    optimise,
    portfolio_stats,
    walk_forward_weights,
)
from algorithmic_trading.risk_sizing import atr_stop, fractional_kelly, risk_based_quantity
from services.price_table import load_returns

st.set_page_config(page_title="Portfolio Optimizer", page_icon="⚖️", layout="wide")
st.title("⚖️ Portfolio Optimizer")
st.warning(
    "RESEARCH ONLY — optimised weights are in-sample estimates and often disappoint out of "
    "sample; the walk-forward comparison below is the honest test. Not advice."
)


@st.cache_data(ttl=600, show_spinner=False)
def _returns(items: tuple[tuple[str, str], ...], period: str):
    return load_returns(dict(items), period)


tab_opt, tab_size = st.tabs(["Optimise", "Position sizing"])
with tab_opt:
    text = st.text_input(
        "Symbols (comma separated): `TCS`, `NSE:TCS`, BSE scrip codes like `500325`, `.BO` tickers",
        "RELIANCE,TCS,HDFCBANK,ITC,INFY,SBIN",
    )
    exchange = st.selectbox("Exchange for plain names", ["NSE", "BSE"])
    period = st.selectbox("History", ["5y", "10y"], index=0)
    cap = st.slider("Maximum weight per stock", 0.1, 1.0, 0.4, 0.05)
    if st.button("Optimise", type="primary"):
        try:
            names = [p for p in text.replace("\n", ",").split(",") if p.strip()]
            typed = parse_holdings("\n".join(f"{n} 1" for n in names))
            tickers, _ = resolve_holdings(typed, exchange)
            if len(tickers) < 2:
                raise ValueError("Enter at least two symbols.")
            rets, missing = _returns(tuple(tickers.items()), period)
            if missing:
                st.warning(f"No price history for {', '.join(missing)}; left out.")
            if rets.shape[1] < 2:
                raise ValueError("Fewer than two symbols had price history.")
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
