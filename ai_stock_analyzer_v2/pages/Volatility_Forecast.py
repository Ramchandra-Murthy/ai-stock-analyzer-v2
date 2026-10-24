"""Volatility Forecast: EWMA vs GARCH(1,1), term structure and an out-of-sample scoreboard."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from algorithmic_trading.strategy_lab import normalise_price_frame
from algorithmic_trading.volatility_forecast import (
    annualised_volatility,
    compare_forecasters,
    ewma_variance,
    fit_garch,
    garch_forecast_series,
    garch_term_structure,
)
from services.resilient_market_data import download_market_frames

st.set_page_config(page_title="Volatility Forecast", page_icon="🌪️", layout="wide")
st.title("🌪️ Volatility Forecast")
st.warning("RESEARCH ONLY — statistical forecasts of risk, not of price direction. Not advice.")


@st.cache_data(ttl=300, show_spinner=False)
def _load(ticker: str, period: str) -> pd.DataFrame | None:
    frames, _ = download_market_frames([ticker], period=period, interval="1d")
    frame = frames.get(ticker.upper())
    return None if frame is None or frame.empty else frame


c1, c2 = st.columns(2)
with c1:
    symbol = st.text_input("Ticker (Yahoo format, e.g. RELIANCE.NS or ^NSEI)", "^NSEI").strip()
with c2:
    period = st.selectbox("History", ["5y", "10y"], index=1)
    horizon = st.slider("Forecast horizon (days)", 5, 60, 30)

if st.button("Forecast", type="primary"):
    raw = _load(symbol, period)
    if raw is None:
        st.error(f"No data returned for {symbol}.")
        st.stop()
    try:
        close = normalise_price_frame(raw)["Close"]
        ret = np.log(close).diff().dropna()
        fit = fit_garch(ret)
        garch = garch_forecast_series(ret, fit)
        ew = ewma_variance(ret)
        ts = garch_term_structure(fit, float(garch.iloc[-1]), int(horizon))
        board = compare_forecasters(ret)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    cols = st.columns(4)
    cols[0].metric("Next-day vol (GARCH, annual)", f"{annualised_volatility(garch.iloc[-1]):.1%}")
    cols[1].metric("Next-day vol (EWMA, annual)", f"{annualised_volatility(ew.iloc[-1]):.1%}")
    cols[2].metric("Long-run vol", f"{annualised_volatility(fit.long_run_variance):.1%}")
    cols[3].metric("Shock half-life", f"{fit.half_life:.0f} days")
    st.markdown("**Forecast path of annualised volatility**")
    st.line_chart(pd.Series([annualised_volatility(v) for v in ts], name="GARCH forecast"))
    st.markdown("**History: GARCH vs EWMA (annualised)**")
    hist = pd.DataFrame({"GARCH": np.sqrt(garch * 252), "EWMA": np.sqrt(ew * 252)}).tail(750)
    st.line_chart(hist)
    st.markdown("**Out-of-sample scoreboard**")
    st.dataframe(board, use_container_width=True)
    st.caption(
        "Scored on next-day squared returns with the QLIKE loss; GARCH is re-fitted on past data "
        "only. If a simple method wins, prefer the simple method."
    )
