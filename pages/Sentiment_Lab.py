"""Sentiment Lab: finance-text sentiment for a stock and a lag-safe check vs returns."""

# ruff: noqa: I001

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.disclaimer import show_disclaimer
from sentiment import (
    daily_sentiment,
    decayed_sentiment,
    information_coefficient,
    quantile_forward_returns,
    score_articles,
    sentiment_features,
    sentiment_signal,
)
from services.news_service import get_company_news
from services.resilient_market_data import download_market_frames

st.set_page_config(page_title="Sentiment Lab", page_icon="🧭", layout="wide")
st.title("🧭 Sentiment Lab")
show_disclaimer()
st.warning(
    "RESEARCH ONLY. A transparent rule-based scorer, not a forecast. Free news feeds only "
    "expose recent articles, so the returns check needs a dated headline archive of your own "
    "(upload a CSV below) before it means anything."
)


@st.cache_data(ttl=600, show_spinner=False)
def _news(symbol: str) -> list[dict]:
    return get_company_news(symbol)


@st.cache_data(ttl=300, show_spinner=False)
def _prices(symbol: str, period: str) -> pd.Series | None:
    frames, _ = download_market_frames([symbol], period=period, interval="1d")
    frame = frames.get(symbol.upper())
    if frame is None or frame.empty or "Close" not in frame.columns:
        return None
    return frame["Close"].astype(float)


c1, c2, c3 = st.columns(3)
symbol = c1.text_input("NSE symbol", "RELIANCE").strip().upper()
half_life = c2.slider("Decay half-life (days)", 1.0, 14.0, 3.0, 0.5)
min_articles = c3.slider("Minimum articles for a call", 1, 10, 3)

upload = st.file_uploader(
    "Optional: dated headlines CSV with columns `date`, `headline`", type=["csv"]
)

if upload is not None:
    raw = pd.read_csv(upload)
    if not {"date", "headline"} <= set(raw.columns):
        st.error("CSV needs `date` and `headline` columns.")
        st.stop()
    scored = score_articles(
        raw.rename(columns={"headline": "title", "date": "published"}), summary_key="_none"
    )
else:
    with st.spinner("Fetching news..."):
        scored = score_articles(_news(symbol))

if scored.empty:
    st.info("No articles found for this symbol.")
    st.stop()

snap = decayed_sentiment(scored, asof=scored["published"].max(), half_life_days=half_life)
call = sentiment_signal(snap["score"], snap["effective_n"], min_articles=min_articles)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Articles", int(snap["n"]))
m2.metric("Decayed sentiment", f"{snap['score']:+.3f}")
m3.metric("Shrunk score", f"{call['shrunk_score']:+.3f}")
m4.metric("Research label", str(call["label"]))
st.caption(
    "Label uses effective sample size (older articles count less) and shrinks toward 0 "
    "when evidence is thin. It is a screening aid, not a buy or sell instruction."
)

daily = daily_sentiment(scored)
feats = sentiment_features(daily)
if not feats.empty:
    st.subheader("Daily sentiment")
    st.line_chart(feats[["score", "ewm"]])

st.subheader("Scored articles")
st.dataframe(
    scored.sort_values("published", ascending=False)[
        ["published", "title", "score", "label", "hits"]
    ],
    use_container_width=True,
)

st.subheader("Does sentiment lead returns?")
e1, e2 = st.columns(2)
horizon = e1.slider("Forward horizon (trading days)", 1, 20, 5)
lag = e2.slider("Lag (trading days after the news)", 0, 5, 1)
prices = _prices(symbol, "5y")
if prices is None or daily.empty:
    st.info("Price history unavailable.")
else:
    ic = information_coefficient(daily["score"], prices, horizon=horizon, lag=lag)
    if ic["n"] < 20:
        st.info(
            f"Only {int(ic['n'])} overlapping days. Need at least 20 (ideally hundreds) "
            "before this is worth reading; upload a longer dated archive."
        )
    else:
        k1, k2, k3 = st.columns(3)
        k1.metric("Rank IC", f"{ic['ic']:+.3f}")
        k2.metric("t-stat (naive)", f"{ic['t_stat']:+.2f}")
        k3.metric("Observations", int(ic["n"]))
        st.caption("Overlapping horizons inflate the t-stat. Treat |IC| < 0.05 as noise.")
        table = quantile_forward_returns(daily["score"], prices, horizon=horizon, lag=lag)
        if not table.empty:
            st.bar_chart(table.set_index("bucket")["mean_fwd_return"])

st.download_button(
    "Download scored articles CSV",
    scored.to_csv(index=False).encode("utf-8"),
    f"{symbol}_sentiment.csv",
    "text/csv",
)
