"""Streamlit dashboard for fundamental AI research."""

# ruff: noqa: I001

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.fundamental_intelligence import (
    fundamental_quality_score,
    normalize_fundamentals,
)

st.set_page_config(
    page_title="AI Fundamental Intelligence",
    page_icon="📊",
    layout="wide",
)
st.title("📊 AI Fundamental Intelligence")
st.caption(
    "Research analytics: normalize company fundamentals and inspect a transparent quality score."
)

st.subheader("Fundamental Input")
col1, col2, col3 = st.columns(3)
revenue = col1.number_input("Revenue growth %", value=10.0)
earnings = col2.number_input("Earnings growth %", value=10.0)
margin = col3.number_input("Profit margin %", value=15.0)
col4, col5, col6 = st.columns(3)
debt = col4.number_input("Debt / Equity", min_value=0.0, value=0.5)
roe = col5.number_input("ROE %", value=15.0)
pe = col6.number_input("P/E", min_value=0.0, value=20.0)

snapshot = normalize_fundamentals(
    {
        "revenue_growth_pct": revenue,
        "earnings_growth_pct": earnings,
        "profit_margin_pct": margin,
        "debt_to_equity": debt,
        "return_on_equity_pct": roe,
        "pe_ratio": pe,
    }
)
score = fundamental_quality_score(snapshot)

st.metric("Fundamental Quality Score", f"{score:.1f}/100")
st.dataframe(
    pd.DataFrame(
        [
            {
                "Revenue Growth %": snapshot.revenue_growth_pct,
                "Earnings Growth %": snapshot.earnings_growth_pct,
                "Profit Margin %": snapshot.profit_margin_pct,
                "Debt / Equity": snapshot.debt_to_equity,
                "ROE %": snapshot.return_on_equity_pct,
                "P/E": snapshot.pe_ratio,
            }
        ]
    ),
    use_container_width=True,
)
st.info("The score is a transparent research metric, not a trading recommendation.")
