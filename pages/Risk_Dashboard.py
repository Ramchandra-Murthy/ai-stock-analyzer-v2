"""Risk Dashboard: VaR, CVaR, correlation, risk contribution and a drawdown circuit breaker."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.lab_inputs import parse_holdings, resolve_holdings
from algorithmic_trading.risk_metrics import (
    breaker_simulation,
    drawdown_series,
    portfolio_returns,
    risk_contributions,
    risk_summary,
)
from services.price_table import load_returns

st.set_page_config(page_title="Risk Dashboard", page_icon="🛡️", layout="wide")
st.title("🛡️ Risk Dashboard")
st.warning("RESEARCH ONLY — historical risk estimates understate tail events. Not advice.")

DEFAULT = "RELIANCE 30\nTCS 25\nHDFCBANK 25\nITC 20"
text = st.text_area(
    "Holdings: one `SYMBOL weight` per line (weights are relative). Accepts `TCS`, `TCS.NS`, "
    "`NSE:TCS`, BSE scrip codes like `500325` or `BSE:500325`, and `.BO` tickers.",
    DEFAULT,
)
c_ex, c_period = st.columns(2)
exchange = c_ex.selectbox(
    "Exchange for plain names", ["NSE", "BSE"], help="Used for symbols with no NSE:/BSE: prefix."
)
period = c_period.selectbox("History", ["2y", "5y"], index=0)
value = st.number_input("Portfolio value (₹)", 10_000.0, value=1_000_000.0, step=50_000.0)
c1, c2 = st.columns(2)
with c1:
    limit = st.slider("Circuit-breaker drawdown limit", 0.03, 0.30, 0.10, 0.01)
with c2:
    cooldown = st.slider("Cooldown (trading days)", 5, 63, 21)


@st.cache_data(ttl=600, show_spinner=False)
def _returns(items: tuple[tuple[str, str], ...], period: str):
    return load_returns(dict(items), period)


if st.button("Analyse", type="primary"):
    try:
        tickers, typed_weights = resolve_holdings(parse_holdings(text), exchange)
        rets, missing = _returns(tuple(tickers.items()), period)
        if missing:
            st.warning(f"No price history for {', '.join(missing)}; left out of the analysis.")
        weights = {name: typed_weights[name] for name in rets.columns}
        summary = risk_summary(rets, weights)
        port = portfolio_returns(rets, weights)
        contrib = risk_contributions(rets, weights)
        sim = breaker_simulation(port, limit, cooldown)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    cols = st.columns(4)
    cols[0].metric(
        "1-day VaR 95%", f"₹{summary['var_95'] * value:,.0f}", f"{summary['var_95']:.2%}"
    )
    cols[1].metric(
        "1-day CVaR 95%", f"₹{summary['cvar_95'] * value:,.0f}", f"{summary['cvar_95']:.2%}"
    )
    cols[2].metric("Annual volatility", f"{summary['annual_volatility']:.1%}")
    cols[3].metric("Max drawdown", f"{summary['max_drawdown']:.1%}")
    st.caption(
        f"99%: VaR {summary['var_99']:.2%}, CVaR {summary['cvar_99']:.2%} of portfolio value. "
        "Historical VaR is the loss exceeded on 5% (or 1%) of past days."
    )
    st.markdown("**Risk contribution (share of variance) vs weight**")
    w = pd.Series(weights) / sum(weights.values())
    st.bar_chart(pd.DataFrame({"Weight": w, "Risk share": contrib}))
    st.markdown("**Correlation**")
    st.dataframe(rets[list(weights)].corr().style.format("{:.2f}"), use_container_width=True)
    st.markdown("**Drawdown**")
    st.area_chart(drawdown_series(port))
    st.markdown(f"**Circuit breaker: flat {cooldown} days after a {limit:.0%} drawdown**")
    st.line_chart((1 + sim).cumprod())
    st.caption(
        "A breaker can lock in losses and miss rebounds; compare both lines before trusting it."
    )
