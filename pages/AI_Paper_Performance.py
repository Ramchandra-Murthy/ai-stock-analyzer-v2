"""Streamlit page for AI paper-trading performance analytics."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.paper_trading import PaperPortfolio
from ai_trading.performance import build_equity_curve, build_performance_report
from components.disclaimer import show_disclaimer

st.set_page_config(
    page_title="AI Paper Performance",
    page_icon="📊",
    layout="wide",
)

st.title("📊 AI Paper Trading Performance")
show_disclaimer()
st.caption("Analytics for the current in-memory AI paper-trading session.")

portfolio = st.session_state.get("ai_paper_portfolio")
prices = st.session_state.get("ai_paper_prices", {})

if not isinstance(portfolio, PaperPortfolio):
    st.info("Run the AI Paper Trading page first to create a paper portfolio.")
    st.stop()

equity = portfolio.equity(prices)
entry_prices: dict[str, float] = {}
for trade in portfolio.trades:
    if trade.side == "BUY":
        entry_prices.setdefault(trade.symbol, trade.price)

report = build_performance_report(
    portfolio.initial_cash,
    portfolio.trades,
    portfolio.positions,
    entry_prices,
    prices,
    equity,
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Paper equity", f"₹{report.current_equity:,.2f}")
m2.metric("Total return", f"{report.total_return_pct:.2f}%")
m3.metric("Total P&L", f"₹{report.total_pnl:,.2f}")
m4.metric("Realized-trade drawdown", f"{report.max_drawdown_pct:.2f}%")

m5, m6, m7, m8 = st.columns(4)
m5.metric("Realized P&L", f"₹{report.realized_pnl:,.2f}")
m6.metric("Unrealized P&L", f"₹{report.unrealized_pnl:,.2f}")
m7.metric("Win rate", f"{report.win_rate_pct:.1f}%")
profit_factor = f"{report.profit_factor:.2f}" if report.profit_factor is not None else "N/A"
m8.metric("Profit factor", profit_factor)

m9, m10 = st.columns(2)
m9.metric("Open exposure", f"{report.gross_exposure_pct:.1f}%")
m10.metric("Closed trade outcomes", report.winning_trades + report.losing_trades)

st.subheader("Equity curve")
curve = build_equity_curve(portfolio.equity_history)
if curve.empty:
    st.info("Run at least one AI paper-trading cycle to build the equity curve.")
else:
    chart = curve.set_index("timestamp")[["equity"]]
    st.line_chart(chart)
    latest_return = float(curve.iloc[-1]["return_pct"])
    latest_drawdown = float(curve.iloc[-1]["drawdown_pct"])
    c1, c2 = st.columns(2)
    c1.metric("Latest cycle return", f"{latest_return:.2f}%")
    c2.metric("Current recorded drawdown", f"{latest_drawdown:.2f}%")
    max_recorded_drawdown = float(curve["drawdown_pct"].max())
    st.metric("Maximum recorded mark-to-market drawdown", f"{max_recorded_drawdown:.2f}%")
    st.dataframe(curve, use_container_width=True, hide_index=True)

st.subheader("Performance breakdown")
breakdown = pd.DataFrame(
    [
        {"metric": "Initial capital", "value": report.initial_cash},
        {"metric": "Current equity", "value": report.current_equity},
        {"metric": "Realized P&L", "value": report.realized_pnl},
        {"metric": "Unrealized P&L", "value": report.unrealized_pnl},
        {"metric": "Total P&L", "value": report.total_pnl},
        {"metric": "Gross exposure %", "value": report.gross_exposure_pct},
        {"metric": "Realized-trade drawdown %", "value": report.max_drawdown_pct},
        {"metric": "Trade count", "value": report.trade_count},
    ]
)
st.dataframe(breakdown, use_container_width=True, hide_index=True)

st.subheader("Trade outcomes")
if portfolio.trades:
    journal = pd.DataFrame(
        [
            {
                "symbol": trade.symbol,
                "side": trade.side,
                "quantity": trade.quantity,
                "price": trade.price,
                "value": trade.value,
                "cash_after": trade.cash_after,
            }
            for trade in portfolio.trades
        ]
    )
    st.dataframe(journal, use_container_width=True, hide_index=True)
else:
    st.info("No paper trades yet.")
