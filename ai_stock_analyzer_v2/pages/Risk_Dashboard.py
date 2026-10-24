"""Risk Dashboard: VaR, CVaR, correlation, risk contribution and a drawdown circuit breaker."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.risk_metrics import (
    breaker_simulation,
    drawdown_series,
    portfolio_returns,
    risk_contributions,
    risk_summary,
)
from services.cached_download import cached_download

st.set_page_config(page_title="Risk Dashboard", page_icon="🛡️", layout="wide")
st.title("🛡️ Risk Dashboard")
st.warning("RESEARCH ONLY — historical risk estimates understate tail events. Not advice.")

DEFAULT = "RELIANCE 30\nTCS 25\nHDFCBANK 25\nITC 20"
text = st.text_area(
    "Holdings: one `SYMBOL weight` per line (NSE symbols, weights are relative)", DEFAULT
)
period = st.selectbox("History", ["2y", "5y"], index=0)
value = st.number_input("Portfolio value (₹)", 10_000.0, value=1_000_000.0, step=50_000.0)
c1, c2 = st.columns(2)
with c1:
    limit = st.slider("Circuit-breaker drawdown limit", 0.03, 0.30, 0.10, 0.01)
with c2:
    cooldown = st.slider("Cooldown (trading days)", 5, 63, 21)


def _parse(raw: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in raw.splitlines():
        parts = line.replace(",", " ").split()
        if len(parts) == 2:
            out[parts[0].upper()] = float(parts[1])
        elif parts:
            raise ValueError(f"Could not read line: {line!r}")
    return out


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


if st.button("Analyse", type="primary"):
    try:
        weights = _parse(text)
        if not weights:
            raise ValueError("Enter at least one holding.")
        rets = _returns(tuple(weights), period)
        if rets.empty:
            raise ValueError("No price data came back. Try again shortly.")
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
