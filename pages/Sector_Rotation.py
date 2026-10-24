"""Sector Rotation: relative-strength quadrants of NSE sector indices vs NIFTY 50."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.sector_rotation import BENCHMARK_TICKER, SECTOR_TICKERS, sector_table
from services.cached_download import cached_download

st.set_page_config(page_title="Sector Rotation", page_icon="🔄", layout="wide")
st.title("🔄 Sector Rotation")
st.warning("RESEARCH ONLY — relative strength is descriptive, not a forecast. Not advice.")
st.caption(
    "Leading = stronger than NIFTY and improving; Weakening = stronger but fading; Lagging = "
    "weaker and fading; Improving = weaker but turning up."
)


@st.cache_data(ttl=600, show_spinner=False)
def _closes(tickers: tuple[str, ...]) -> pd.DataFrame:
    raw = cached_download(list(tickers), period="2y", auto_adjust=True, progress=False)
    if raw is None or raw.empty or not isinstance(raw.columns, pd.MultiIndex):
        return pd.DataFrame()
    return raw["Close"].dropna(how="all")


if st.button("Load sectors", type="primary"):
    tickers = (BENCHMARK_TICKER, *SECTOR_TICKERS.values())
    close = _closes(tickers)
    if close.empty or BENCHMARK_TICKER not in close:
        st.error("Index data was unavailable. Try again shortly.")
        st.stop()
    names = {v: k for k, v in SECTOR_TICKERS.items()}
    sectors = close.drop(columns=[BENCHMARK_TICKER]).rename(columns=names)
    missing = [
        k for k, v in SECTOR_TICKERS.items() if v not in close.columns or close[v].isna().all()
    ]
    try:
        table = sector_table(sectors, close[BENCHMARK_TICKER])
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    if missing:
        st.info(
            "No data for: " + ", ".join(missing) + " (the data source may use different symbols)."
        )
    st.dataframe(
        table.style.format(
            {c: "{:.1%}" for c in table.columns if "return" in c or "vs index" in c}
            | {"RS ratio": "{:.1f}", "RS momentum": "{:.1f}"},
            na_rep="n/a",
        ),
        use_container_width=True,
    )
    st.scatter_chart(table.reset_index(), x="RS ratio", y="RS momentum", color="Quadrant")
