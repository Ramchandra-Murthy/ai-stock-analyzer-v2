"""Risk Guards Lab: what stop-loss, take-profit, trailing stop and a kill switch really do."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.risk_guards import GuardConfig, compare_guards, sma_crossover_signal
from components.disclaimer import show_disclaimer
from services.resilient_market_data import download_market_frames
from services.symbol_resolver import resolve_symbol

st.set_page_config(page_title="Risk Guards Lab", page_icon="🚧", layout="wide")
st.title("🚧 Risk Guards Lab")
show_disclaimer()
st.caption(
    "Tests protective rules on a moving-average trend strategy using daily closes. A stop is "
    "assumed to fill at the close of the day it is breached, so real stops can fill worse on "
    "gaps. After a guard exits, the strategy waits for its signal to turn off and on again "
    "before re-entering. Guards often lower drawdown and also cut returns; this shows the trade-off."
)


@st.cache_data(ttl=600, show_spinner=False)
def _closes(ticker: str, period: str) -> pd.Series | None:
    frames, _ = download_market_frames([ticker], period=period, interval="1d")
    frame = frames.get(ticker.upper())
    if frame is None or frame.empty or "Close" not in frame:
        return None
    return pd.to_numeric(frame["Close"], errors="coerce").dropna()


c1, c2, c3 = st.columns(3)
symbol = c1.text_input("Symbol", "RELIANCE").strip()
period = c2.selectbox("History", ["5y", "10y"], index=0)
cost = c3.number_input("Cost per side (bps)", 0.0, 100.0, 10.0, 1.0)
c4, c5 = st.columns(2)
fast = int(c4.number_input("Fast average (days)", 5, 100, 20, 1))
slow = int(c5.number_input("Slow average (days)", 20, 300, 50, 5))
st.markdown("**Guards** (tick to enable)")
g1, g2, g3, g4 = st.columns(4)
stop = g1.slider("Stop-loss %", 2, 30, 8) / 100 if g1.checkbox("Stop-loss", True) else None
take = g2.slider("Take-profit %", 5, 80, 20) / 100 if g2.checkbox("Take-profit") else None
trail = (
    g3.slider("Trailing stop %", 2, 30, 10) / 100 if g3.checkbox("Trailing stop", True) else None
)
kill = g4.slider("Kill-switch drawdown %", 5, 50, 20) / 100 if g4.checkbox("Kill switch") else None

if st.button("Run comparison", type="primary"):
    try:
        ticker = resolve_symbol(symbol).ticker
        close = _closes(ticker, period)
        if close is None:
            st.error(f"No price data for {ticker}.")
            st.stop()
        signal = sma_crossover_signal(close, fast, slow)
        plain, guarded = compare_guards(
            close,
            signal,
            GuardConfig(
                stop_loss=stop,
                take_profit=take,
                trailing_stop=trail,
                kill_switch_drawdown=kill,
                cost_bps=float(cost),
            ),
        )
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    buy_hold = float(close.iloc[-1] / close.iloc[0] - 1.0)
    m = st.columns(4)
    m[0].metric("No guards", f"{plain.total_return:.1%}", f"max drawdown {plain.max_drawdown:.1%}")
    m[1].metric(
        "With guards",
        f"{guarded.total_return:.1%}",
        f"max drawdown {guarded.max_drawdown:.1%}",
    )
    m[2].metric("Buy and hold", f"{buy_hold:.1%}")
    m[3].metric("Trades", f"{len(plain.trades)} → {len(guarded.trades)}")
    if guarded.killed_on is not None:
        st.warning(f"Kill switch fired on {guarded.killed_on:%d %b %Y}; no trades after that.")
    curves = pd.concat(
        [plain.equity.rename("No guards"), guarded.equity.rename("With guards")], axis=1
    )
    st.line_chart(curves)
    if guarded.exits_by_reason:
        st.markdown("**How trades ended (with guards)**")
        st.dataframe(
            pd.Series(guarded.exits_by_reason, name="Trades").to_frame(), use_container_width=True
        )
    if not guarded.trades.empty:
        view = guarded.trades.assign(**{"return": (guarded.trades["return"] * 100).round(2)})
        st.markdown("**Trade list (return in %)**")
        st.dataframe(view.tail(50), use_container_width=True)
