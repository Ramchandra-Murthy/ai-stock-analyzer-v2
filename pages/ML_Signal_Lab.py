"""ML Signal Lab: leakage-safe walk-forward machine-learning signals (research only)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.ml_signals import MODELS, run_ml_strategy
from algorithmic_trading.strategy_lab import normalise_price_frame
from algorithmic_trading.trading_costs import india_cost_model
from services.resilient_market_data import download_market_frames

st.set_page_config(page_title="ML Signal Lab", page_icon="🧬", layout="wide")
st.title("🧬 ML Signal Lab")
st.warning(
    "RESEARCH ONLY — most ML 'edges' vanish out of sample. Results are historical, not "
    "forecasts, and no orders are placed."
)
st.caption(
    "Features use only past data; training rows whose label window would touch the test period "
    "are purged; predictions come from walk-forward windows and trade on the next bar. Compare "
    "accuracy with the always-up base rate before believing anything."
)


@st.cache_data(ttl=300, show_spinner=False)
def _load(ticker: str, period: str) -> pd.DataFrame | None:
    frames, _ = download_market_frames([ticker], period=period, interval="1d")
    frame = frames.get(ticker.upper())
    return None if frame is None or frame.empty else frame


c1, c2 = st.columns(2)
with c1:
    symbol = st.text_input("NSE symbol", "RELIANCE").strip().upper()
    period = st.selectbox("History", ["5y", "10y"], index=1)
    model = st.selectbox("Model", MODELS)
with c2:
    horizon = st.slider("Prediction horizon (days)", 1, 20, 5)
    threshold = st.slider("Go long above probability", 0.50, 0.70, 0.55, 0.01)
    train_bars = st.number_input("Training window (days)", 300, 2000, 756, 21)

if st.button("Run walk-forward ML", type="primary"):
    raw = _load(f"{symbol}.NS", period)
    if raw is None:
        st.error(f"No data returned for {symbol}.")
        st.stop()
    try:
        with st.spinner("Training in walk-forward windows..."):
            res = run_ml_strategy(
                normalise_price_frame(raw),
                model=model,
                horizon=int(horizon),
                embargo=int(horizon),
                threshold=float(threshold),
                train_bars=int(train_bars),
                cost_model=india_cost_model("delivery", slippage_bps=5.0),
            )
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    m = res.metrics
    start = res.probabilities.first_valid_index()
    curve = res.curve.loc[start:]
    ret = curve["strategy_equity"].iloc[-1] / curve["strategy_equity"].iloc[0] - 1
    bh = curve["buy_hold_equity"].iloc[-1] / curve["buy_hold_equity"].iloc[0] - 1
    cols = st.columns(4)
    cols[0].metric("Out-of-sample return", f"{ret:.1%}", f"buy & hold {bh:.1%}")
    cols[1].metric("Direction accuracy", f"{res.accuracy:.1%}", f"base rate {res.base_rate:.1%}")
    cols[2].metric(
        "Sharpe (whole run)", "n/a" if m.sharpe_ratio is None else f"{m.sharpe_ratio:.2f}"
    )
    cols[3].metric("Windows", res.windows)
    if res.accuracy <= res.base_rate + 0.01:
        st.warning("Accuracy is not meaningfully above simply guessing the more common direction.")
    st.line_chart(
        curve[["strategy_equity", "buy_hold_equity"]]
        / curve[["strategy_equity", "buy_hold_equity"]].iloc[0]
    )
    st.markdown("**Feature influence** (descriptive, from the last window only)")
    st.bar_chart(res.importances)
