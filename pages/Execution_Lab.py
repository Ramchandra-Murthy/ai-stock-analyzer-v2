"""Execution Lab: compare TWAP, VWAP and participation schedules on a real session (research)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from algorithmic_trading.execution import (
    pov_schedule,
    simulate_execution,
    twap_schedule,
    vwap_schedule,
)
from components.disclaimer import show_disclaimer
from services.resilient_market_data import download_market_frames
from services.symbol_resolver import resolve_symbol

st.set_page_config(page_title="Execution Lab", page_icon="⚙️", layout="wide")
st.title("⚙️ Execution Lab")
show_disclaimer()
st.caption(
    "How you slice a large order changes what it costs. This replays one real trading session "
    "(5-minute bars) and charges each slice half the spread plus a square-root market-impact "
    "estimate. It is a stylised model, not a forecast of broker fills, and no orders are placed."
)


@st.cache_data(ttl=300, show_spinner=False)
def _session(ticker: str) -> tuple[pd.DataFrame, float, float] | None:
    frames, _ = download_market_frames([ticker], period="1mo", interval="5m")
    frame = frames.get(ticker.upper())
    if frame is None or frame.empty:
        return None
    frame = frame[["Close", "Volume"]].dropna()
    days = frame.groupby(frame.index.date)
    daily_volume = days["Volume"].sum()
    daily_close = days["Close"].last()
    if len(daily_volume) < 3:
        return None
    adv = float(daily_volume.iloc[:-1].mean())
    vol = float(daily_close.pct_change().std()) if len(daily_close) > 3 else 0.015
    last = frame[pd.Index(frame.index.date) == frame.index.date[-1]]
    return last, adv, vol


c1, c2, c3 = st.columns(3)
symbol = c1.text_input("Symbol", "RELIANCE").strip()
side = c2.selectbox("Side", ["buy", "sell"])
shares = int(c3.number_input("Order size (shares)", 100, 50_000_000, 200_000, 1000))
c4, c5, c6 = st.columns(3)
k = c4.slider("Impact coefficient k", 0.1, 1.5, 0.5, 0.05, help="Higher for illiquid stocks.")
spread = c5.slider("Half spread (bps)", 0.0, 20.0, 2.0, 0.5)
pov = c6.slider("Participation rate", 0.01, 0.30, 0.10, 0.01)

if st.button("Compare schedules", type="primary"):
    try:
        ticker = resolve_symbol(symbol).ticker
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    data = _session(ticker)
    if data is None:
        st.error(f"No usable intraday history for {ticker} (needs several recent sessions).")
        st.stop()
    bars, adv, daily_vol = data
    px, vol = bars["Close"].to_numpy(), bars["Volume"].to_numpy()
    n = len(px)
    st.caption(
        f"Session {bars.index[0]:%d %b %Y}: {n} bars · average daily volume {adv:,.0f} · "
        f"daily volatility {daily_vol:.2%} · order = {shares / adv:.1%} of a day's volume."
    )
    if shares > 0.2 * adv:
        st.warning("This order is over 20% of average daily volume; real impact would be larger.")
    schedules = {
        "Single block (at arrival)": np.array([shares] + [0] * (n - 1)),
        "TWAP (equal slices)": twap_schedule(shares, n),
        "VWAP (volume-weighted)": vwap_schedule(shares, np.maximum(vol, 1.0)),
        f"Participation {pov:.0%}": pov_schedule(shares, vol, pov),
    }
    rows, results = [], {}
    for name, schedule in schedules.items():
        if schedule.sum() == 0:
            continue
        res = simulate_execution(
            side, schedule, px, vol, adv=adv, daily_vol=daily_vol, k=k, half_spread_bps=spread
        )
        results[name] = res
        rows.append(
            {
                "Schedule": name,
                "Filled": f"{res.filled:,} of {shares:,}",
                "Avg price": round(res.average_price, 2),
                "Shortfall (bps)": round(res.shortfall_bps, 1),
                "Shortfall (₹)": round(res.shortfall_rupees),
                "Impact (bps)": round(res.impact_bps, 1),
                "Drift (bps)": round(res.drift_bps, 1),
                "vs session VWAP (bps)": round(res.vs_vwap_bps, 1),
            }
        )
    st.dataframe(pd.DataFrame(rows).set_index("Schedule"), use_container_width=True)
    st.caption(
        "Shortfall = what you paid (or received) versus the arrival price, positive is worse for "
        "you. Impact is the model's cost of your own size; drift is the market moving while you "
        "traded. Splitting lowers impact but exposes you to drift, which can go either way."
    )
    chart = pd.DataFrame(
        {name: res.fills["shares"].cumsum() for name, res in results.items()}
    ).set_index(bars.index)
    st.markdown("**Cumulative shares filled**")
    st.line_chart(chart)
