"""Options Strategy Builder: payoff, breakevens and Greeks for common structures (analysis only)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from algorithmic_trading.options_strategies import (
    DEFAULT_NIFTY_LOT_SIZE,
    TEMPLATES,
    aggregate_greeks,
    build_template,
    expiry_payoff,
    iv_rank_percentile,
    payoff_summary,
)
from services.cached_download import cached_download

st.set_page_config(page_title="Options Strategy Builder", page_icon="🧩", layout="wide")
st.title("🧩 Options Strategy Builder")
st.warning(
    "ANALYSIS ONLY — theoretical payoffs, not advice and no orders. Margin is NOT calculated: "
    "short options can require large margin and carry large or unlimited loss."
)


@st.cache_data(ttl=600, show_spinner=False)
def _vix_history() -> pd.Series:
    raw = cached_download("^INDIAVIX", period="2y", progress=False)
    if raw is None or raw.empty:
        return pd.Series(dtype=float)
    close = raw["Close"]
    return (close.iloc[:, 0] if isinstance(close, pd.DataFrame) else close).dropna()


left, right = st.columns(2)
with left:
    spot = st.number_input("Underlying price", 1.0, value=25_000.0, step=10.0)
    step = st.number_input("Strike step", 1.0, value=50.0, step=1.0)
    template = st.selectbox("Strategy", TEMPLATES)
    width = st.slider("Width (strike steps)", 1, 20, 4)
with right:
    days = st.number_input("Days to expiry", 1, 365, 7)
    vol_pct = st.number_input("Implied volatility used for pricing (%)", 1.0, 200.0, 15.0, 0.5)
    rate_pct = st.number_input("Risk-free rate (%)", 0.0, 20.0, 6.5, 0.1)
    lot = st.number_input(
        "Lot size",
        1,
        10_000,
        DEFAULT_NIFTY_LOT_SIZE,
        1,
        help="NIFTY lot size changes by NSE circular (65 from Jan 2026 per broker notes). "
        "Verify against NSE before relying on rupee figures.",
    )
    lots = st.number_input("Lots", 1, 1000, 1)

st.caption(
    "Premiums are Black-Scholes at your volatility — not market quotes. Replace them with live chain prices before judging a trade."
)

try:
    legs = build_template(
        template,
        spot=float(spot),
        strike_step=float(step),
        width_steps=int(width),
        days_to_expiry=float(days),
        rate=rate_pct / 100,
        vol=vol_pct / 100,
    )
except ValueError as exc:
    st.error(str(exc))
    st.stop()

summary = payoff_summary(legs)
mult = float(lot) * int(lots)
fmt = lambda v: "Unlimited" if v is None else f"₹{v * mult:,.0f}"  # noqa: E731
cols = st.columns(4)
net = summary["net_premium"]
cols[0].metric("Net debit" if net > 0 else "Net credit", f"₹{abs(net) * mult:,.0f}")
cols[1].metric("Max profit", fmt(summary["max_profit"]))
cols[2].metric("Max loss", fmt(summary["max_loss"]))
cols[3].metric("Breakevens", ", ".join(f"{b:,.0f}" for b in summary["breakevens"]) or "none")

spots = np.linspace(spot * 0.85, spot * 1.15, 241)
st.line_chart(pd.DataFrame({"P/L at expiry (₹)": expiry_payoff(legs, spots) * mult}, index=spots))
st.dataframe(
    pd.DataFrame(
        [
            {
                "Leg": f"{'Long' if l.qty > 0 else 'Short'} {abs(l.qty)} {l.kind}",
                "Strike": l.strike,
                "Premium": round(l.premium, 2),
            }
            for l in legs
        ]
    ),
    hide_index=True,
)
g = aggregate_greeks(
    legs, spot=float(spot), days_to_expiry=float(days), rate=rate_pct / 100, vol=vol_pct / 100
)
gc = st.columns(4)
gc[0].metric("Delta (per lot)", f"{g['delta'] * lot:.1f}")
gc[1].metric("Gamma (per lot)", f"{g['gamma'] * lot:.4f}")
gc[2].metric("Vega per vol pt (₹/lot)", f"{g['vega'] * lot:,.0f}")
gc[3].metric("Theta per day (₹/lot)", f"{g['theta'] * lot:,.0f}")

vix = _vix_history()
if len(vix) >= 30:
    r = iv_rank_percentile(vix)
    st.info(
        f"India VIX {r['current']:.1f}: IV rank {r['rank']:.0%}, percentile {r['percentile']:.0%} "
        f"over the last year (range {r['low']:.1f}–{r['high']:.1f}). High rank favours "
        "selling premium and low rank favours buying it, as a rule of thumb, not a signal."
    )
else:
    st.caption("India VIX history was unavailable, so IV rank is not shown.")
