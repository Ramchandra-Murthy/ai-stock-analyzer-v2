"""Streamlit dashboard for AI paper-trading journal analytics."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.trade_journal import build_trade_journal, summarize_journal

st.set_page_config(
    page_title="AI Paper Trade Journal",
    page_icon="📒",
    layout="wide",
)

st.title("📒 AI Paper Trade Journal")
st.caption("Completed round-trip analytics for the current in-memory AI paper-trading session.")

portfolio = st.session_state.get("ai_paper_portfolio")

if portfolio is None:
    st.info("Run the AI Paper Trading page first to create a paper portfolio.")
    st.stop()

rows = build_trade_journal(portfolio.trades)
summary = summarize_journal(rows)

if not rows:
    st.info("No completed paper trades yet.")
    st.stop()

total_pnl = sum(row.pnl for row in rows)
wins = sum(row.pnl > 0 for row in rows)
losses = sum(row.pnl < 0 for row in rows)
avg_holding = sum(row.holding_seconds for row in rows) / len(rows)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Completed trades", len(rows))
m2.metric("Total realized P&L", f"₹{total_pnl:,.2f}")
m3.metric("Win rate", f"{wins / len(rows) * 100.0:.1f}%")
m4.metric("Avg holding", f"{avg_holding / 3600.0:.2f} h")

st.subheader("Trade journal")
journal = pd.DataFrame(
    [
        {
            "symbol": row.symbol,
            "entry": row.entry_price,
            "exit": row.exit_price,
            "quantity": row.quantity,
            "P&L": row.pnl,
            "return %": row.return_pct,
            "holding hours": row.holding_seconds / 3600.0,
            "ML confidence %": row.entry_confidence_pct,
            "entry reason": row.entry_reason,
            "exit reason": row.exit_reason,
        }
        for row in rows
    ]
)
st.dataframe(journal, use_container_width=True, hide_index=True)

st.subheader("Symbol statistics")
st.dataframe(
    pd.DataFrame(summary),
    use_container_width=True,
    hide_index=True,
)
