"""Streamlit dashboard for transparent AI news sentiment research."""

# ruff: noqa: I001

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.news_sentiment import aggregate_sentiment, summarize_news

st.set_page_config(page_title="AI News Sentiment", page_icon="📰", layout="wide")
st.title("📰 AI News & Sentiment Intelligence")
st.caption("Research monitor: transparent headline sentiment. No live orders are placed.")

text = st.text_area(
    "Paste headlines (one per line)",
    placeholder="Company reports strong profit growth\nCompany faces weak demand",
    height=180,
    key="ai_news_headlines_input",
)
analyze = st.button("Analyze Headlines", type="primary")

if analyze:
    st.session_state["ai_news_headlines"] = text
elif "ai_news_headlines" not in st.session_state:
    st.session_state["ai_news_headlines"] = ""

headlines = [
    line.strip() for line in st.session_state["ai_news_headlines"].splitlines() if line.strip()
]
news = pd.DataFrame({"headline": headlines})
summary = summarize_news(news)
metrics = aggregate_sentiment(news)

col1, col2, col3 = st.columns(3)
col1.metric("Headlines", int(metrics["headlines"]))
col2.metric("Sentiment", str(metrics["label"]))
col3.metric("Score", f"{float(metrics['sentiment_score']):.3f}")

st.subheader("Headline Analysis")
st.dataframe(summary, use_container_width=True)

if not summary.empty:
    st.bar_chart(summary.set_index("headline")["score"])

st.download_button(
    "Download Sentiment CSV",
    summary.to_csv(index=False).encode("utf-8"),
    "ai_news_sentiment.csv",
    "text/csv",
)
