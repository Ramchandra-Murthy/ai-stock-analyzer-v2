"""Performance Attribution: alpha vs beta, rolling Sharpe and who drove the return (research)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.attribution import (
    factor_regression,
    return_contributions,
    rolling_max_drawdown,
    rolling_sharpe,
)
from algorithmic_trading.lab_inputs import parse_holdings, resolve_holdings
from algorithmic_trading.risk_metrics import portfolio_returns
from components.disclaimer import show_disclaimer
from services.cached_download import cached_download
from services.price_table import load_returns

st.set_page_config(page_title="Performance Attribution", page_icon="🧭", layout="wide")
st.title("🧭 Performance Attribution")
show_disclaimer()
st.caption(
    "Splits a portfolio's past return into market exposure (beta) and what is left (alpha), "
    "and shows how its risk-adjusted performance changed over time. With a short history the "
    "alpha estimate is very noisy; read the t-statistic before believing it."
)

text = st.text_area(
    "Holdings: one `SYMBOL weight` per line (NSE names, BSE codes, `.NS`/`.BO` accepted)",
    "RELIANCE 30\nTCS 25\nHDFCBANK 25\nITC 20",
)
c1, c2, c3 = st.columns(3)
exchange = c1.selectbox("Exchange for plain names", ["NSE", "BSE"])
period = c2.selectbox("History", ["2y", "3y", "5y"], index=1)
rf = c3.number_input("Risk-free rate (annual %)", 0.0, 15.0, 6.5, 0.25) / 100
factor_text = st.text_input(
    "Factor tickers (comma separated Yahoo tickers)",
    "^NSEI",
    help="^NSEI is NIFTY 50. Add another index, e.g. ^NSMIDCP, to test a second exposure.",
)


@st.cache_data(ttl=900, show_spinner=False)
def _factor_returns(tickers: tuple[str, ...], span: str) -> pd.DataFrame:
    cols = {}
    for ticker in tickers:
        raw = cached_download(ticker, period=span, progress=False)
        if raw is None or raw.empty:
            continue
        close = raw["Close"]
        close = close.iloc[:, 0] if isinstance(close, pd.DataFrame) else close
        cols[ticker] = close.pct_change().dropna()
    return pd.DataFrame(cols)


if st.button("Analyse", type="primary"):
    try:
        names, weights = resolve_holdings(parse_holdings(text), exchange)
        returns, missing = load_returns(names, period)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    if missing:
        st.warning("No data for: " + ", ".join(missing) + ". The rest were analysed.")
    kept = {n: w for n, w in weights.items() if n in returns.columns}
    port = portfolio_returns(returns, kept)
    tickers = tuple(t.strip() for t in factor_text.split(",") if t.strip())
    factors = _factor_returns(tickers, period)
    st.markdown("**Factor attribution**")
    if factors.empty:
        st.info("No factor data came back; showing the portfolio-only views below.")
    else:
        try:
            fit = factor_regression(port, factors, risk_free_annual=rf)
            cols = st.columns(3 + len(fit.betas))
            cols[0].metric("Alpha (annual)", f"{fit.alpha_annual:.1%}", f"t = {fit.alpha_t:.2f}")
            cols[1].metric("R²", f"{fit.r_squared:.0%}")
            cols[2].metric("Residual vol", f"{fit.residual_vol_annual:.1%}")
            for col, (name, beta) in zip(cols[3:], fit.betas.items(), strict=True):
                col.metric(f"Beta to {name}", f"{beta:.2f}", f"t = {fit.beta_t[name]:.1f}")
            if abs(fit.alpha_t) < 2:
                st.info(
                    "Alpha is not statistically distinguishable from zero (|t| < 2): the "
                    "excess return could be luck. Most of the return is explained by the market."
                )
            st.caption(f"{fit.observations} overlapping days.")
        except ValueError as exc:
            st.warning(str(exc))
    st.markdown("**Rolling risk-adjusted performance**")
    window = 63
    roll = pd.concat(
        [rolling_sharpe(port, window, rf), rolling_max_drawdown(port, 126)], axis=1
    ).dropna(how="all")
    left, right = st.columns(2)
    left.caption("Rolling 63-day Sharpe ratio")
    left.line_chart(roll["rolling_sharpe"])
    right.caption("Worst drawdown inside each 126-day window")
    right.line_chart(roll["rolling_max_drawdown"])
    st.markdown("**Who drove the return** (sum of weight × daily return)")
    contrib = return_contributions(returns, kept)
    st.bar_chart(contrib)
    st.dataframe((contrib * 100).round(2).rename("Contribution (% points)").to_frame())
