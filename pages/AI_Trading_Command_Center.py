"""Integrated AI trading command center.

Combines the existing live 20-stock board, ML scanner, paper portfolio,
risk controls, and performance analytics in one research/paper-trading page.
No broker orders are created or submitted.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from ai_trading.ml_scanner import scan_universe
from ai_trading.paper_trading import PaperPortfolio, apply_ml_signals
from ai_trading.performance import build_performance_report
from ai_trading.risk import RiskLimits, risk_warnings
from modules.intraday import _fetch_live_board, _market_session_is_open
from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES
from services.cached_download import cached_download

IST = ZoneInfo("Asia/Kolkata")

st.set_page_config(
    page_title="AI Trading Command Center",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 AI Trading Command Center")
st.caption(
    "One research workflow: Live 20 → ML validation → risk controls → paper execution → performance. "
    "Simulation only; no broker orders are submitted."
)

if "ai_paper_portfolio" not in st.session_state:
    st.session_state.ai_paper_portfolio = PaperPortfolio(initial_cash=100_000.0)

portfolio = st.session_state.ai_paper_portfolio

left, mid, right = st.columns(3)
with left:
    ml_per_exchange = st.slider(
        "ML candidates per exchange",
        2,
        5,
        5,
        1,
        help="Uses the strongest names currently present on the Live 20 board, split by exchange.",
    )
with mid:
    horizon = st.slider("ML horizon (days)", 1, 20, 5)
    threshold = st.slider("ML threshold (%)", 0.0, 5.0, 1.0, 0.5)
with right:
    capital_fraction = st.slider("Capital per paper cycle", 0.05, 1.0, 0.20, 0.05)
    max_positions = st.slider("Maximum paper positions", 1, 10, 5)

st.subheader("Risk controls")
r1, r2, r3 = st.columns(3)
with r1:
    max_exposure_pct = st.slider("Maximum exposure", 20.0, 100.0, 80.0, 5.0)
with r2:
    max_position_pct = st.slider("Maximum position", 5.0, 50.0, 20.0, 5.0)
with r3:
    cash_reserve_pct = st.slider("Minimum cash reserve", 0.0, 50.0, 10.0, 5.0)

risk_limits = RiskLimits(
    max_exposure_pct=max_exposure_pct,
    max_position_pct=max_position_pct,
    cash_reserve_pct=cash_reserve_pct,
)

now = datetime.now(IST)
market_open = _market_session_is_open(now)

status_cols = st.columns(4)
status_cols[0].metric("Market", "OPEN" if market_open else "CLOSED")
status_cols[1].metric(
    "Paper equity",
    f"₹{portfolio.equity(st.session_state.get('ai_paper_prices', {})):,.0f}",
)
status_cols[2].metric("Open positions", len(portfolio.positions))
status_cols[3].metric("Paper fills", len(portfolio.trades))

if not market_open:
    st.info(
        f"Market is closed at {now:%Y-%m-%d %H:%M IST}. "
        "The command center will not run a new live-board/ML paper cycle."
    )

run_cycle = st.button(
    "▶ Run Command Center Cycle",
    type="primary",
    disabled=not market_open,
    use_container_width=True,
)

if run_cycle:
    with st.spinner("Loading Live 20 market board..."):
        board, live_signals, sector_summary, live_stats = _fetch_live_board()

    if board.empty:
        st.error("Live 20 board returned no usable market data. No paper trades were changed.")
        st.stop()

    st.session_state["command_center_board"] = board
    st.session_state["command_center_live_signals"] = live_signals
    st.session_state["command_center_sector_summary"] = sector_summary
    st.session_state["command_center_live_stats"] = live_stats

    candidates = {"NSE": [], "BSE": []}
    for exchange in ("NSE", "BSE"):
        names = board.loc[board["Exchange"].eq(exchange), "Symbol"].astype(str).str.upper().tolist()
        candidates[exchange] = names[:ml_per_exchange]

    results = []
    with st.spinner("Running leakage-safe ML validation on Live 20 candidates..."):
        for exchange, symbols in candidates.items():
            if not symbols:
                continue
            universe = NSE_CANDIDATES if exchange == "NSE" else BSE_CANDIDATES
            ordered = [symbol for symbol in symbols if symbol in universe]
            if not ordered:
                continue
            try:
                result = scan_universe(
                    ordered,
                    exchange=exchange,
                    period="5y",
                    horizon=horizon,
                    threshold=threshold / 100.0,
                )
            except (TypeError, ValueError, KeyError) as exc:
                st.warning(f"{exchange} ML scan skipped: {exc}")
                continue
            if not result.empty:
                results.append(result)

    ml_result = pd.concat(results, ignore_index=True) if results else pd.DataFrame()
    st.session_state["command_center_ml"] = ml_result

    if ml_result.empty:
        st.warning("No valid ML results were produced. Paper positions were not changed.")
    else:
        tickers = [
            (
                f"{str(symbol).strip().upper()}.NS"
                if exchange == "NSE"
                else f"{str(symbol).strip().upper()}.BO"
            )
            for symbol, exchange in zip(ml_result["symbol"], ml_result["exchange"], strict=True)
        ]
        prices_data = cached_download(
            tickers,
            period="5d",
            ttl=60.0,
            auto_adjust=False,
            progress=False,
            threads=False,
        )

        prices: dict[str, float] = {}
        if isinstance(prices_data.columns, pd.MultiIndex):
            close_data = prices_data["Close"]
            for symbol, ticker in zip(ml_result["symbol"], tickers, strict=True):
                if ticker in close_data:
                    series = pd.to_numeric(close_data[ticker], errors="coerce").dropna()
                    if not series.empty:
                        prices[str(symbol).upper()] = float(series.iloc[-1])
        elif "Close" in prices_data and len(ml_result) == 1:
            series = pd.to_numeric(prices_data["Close"], errors="coerce").dropna()
            if not series.empty:
                prices[str(ml_result.iloc[0]["symbol"]).upper()] = float(series.iloc[-1])

        fills = apply_ml_signals(
            portfolio,
            ml_result,
            prices,
            capital_fraction=capital_fraction,
            max_positions=max_positions,
            risk_limits=risk_limits,
        )
        st.session_state["ai_paper_prices"] = prices
        portfolio.record_equity(prices)
        st.session_state["command_center_fills"] = fills
        st.success(f"Cycle complete: {len(fills)} simulated paper fills.")

board = st.session_state.get("command_center_board", pd.DataFrame())
ml_result = st.session_state.get("command_center_ml", pd.DataFrame())
prices = st.session_state.get("ai_paper_prices", {})

if not board.empty:
    st.subheader("1. Live 20 Market Board")
    display = [
        column
        for column in [
            "Rank",
            "Symbol",
            "Exchange",
            "Price",
            "1-min change %",
            "5-min change %",
            "Today change %",
            "Volume surge x",
            "Breakout",
            "Relative Strength",
            "Last update",
        ]
        if column in board.columns
    ]
    st.dataframe(board[display], use_container_width=True, hide_index=True)

    live_stats = st.session_state.get("command_center_live_stats", {})
    st.caption(
        f"Live scan: {live_stats.get('scan_seconds', 'N/A')}s · "
        f"usable quotes: {live_stats.get('usable', 'N/A')} · "
        "provider data may be delayed."
    )

if not ml_result.empty:
    st.subheader("2. ML Validation on Live Candidates")
    cols = [
        column
        for column in [
            "symbol",
            "exchange",
            "latest_price",
            "signal",
            "confidence_pct",
            "probability_up_pct",
            "validation_pct",
            "trend_pct",
            "regime",
            "decision_reason",
        ]
        if column in ml_result.columns
    ]
    st.dataframe(
        ml_result.sort_values("confidence_pct", ascending=False)[cols],
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "These are historical/model measurements used for research and paper trading; "
        "confidence is not a forecast guarantee."
    )

equity = portfolio.equity(prices)
market_value = sum(
    quantity * float(prices[symbol])
    for symbol, quantity in portfolio.positions.items()
    if symbol in prices
)
warnings = risk_warnings(equity, portfolio.cash, market_value, risk_limits)

st.subheader("3. Risk Gate")
for warning in warnings:
    st.warning(warning)
if not warnings:
    st.success("Current paper portfolio is within the configured portfolio risk limits.")

risk_cols = st.columns(4)
risk_cols[0].metric("Exposure", f"{market_value / equity * 100.0:.1f}%" if equity else "0.0%")
risk_cols[1].metric("Cash reserve", f"{portfolio.cash / equity * 100.0:.1f}%" if equity else "0.0%")
risk_cols[2].metric("Max exposure", f"{risk_limits.max_exposure_pct:.0f}%")
risk_cols[3].metric("Max position", f"{risk_limits.max_position_pct:.0f}%")

st.subheader("4. Paper Portfolio")
if portfolio.positions:
    position_rows = []
    for symbol, quantity in portfolio.positions.items():
        price = prices.get(symbol)
        value = quantity * float(price) if price is not None else 0.0
        position_rows.append(
            {
                "Symbol": symbol,
                "Quantity": quantity,
                "Price": price,
                "Market value": value,
                "Portfolio %": value / equity * 100.0 if equity else 0.0,
            }
        )
    st.dataframe(position_rows, use_container_width=True, hide_index=True)
else:
    st.info("No open paper positions.")

if portfolio.trades:
    st.caption(f"Last paper cycle fills: {len(st.session_state.get('command_center_fills', []))}")

st.subheader("5. Performance")
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

p1, p2, p3, p4, p5 = st.columns(5)
p1.metric("Total return", f"{report.total_return_pct:.2f}%")
p2.metric("Total P&L", f"₹{report.total_pnl:,.2f}")
p3.metric("Win rate", f"{report.win_rate_pct:.1f}%")
p4.metric(
    "Profit factor",
    f"{report.profit_factor:.2f}" if report.profit_factor is not None else "N/A",
)
p5.metric("Realized-trade drawdown", f"{report.max_drawdown_pct:.2f}%")

st.caption(
    "Recommended workflow: run cycles in paper mode, collect a meaningful trade sample, "
    "review return, drawdown, win rate, profit factor and costs, and only then consider "
    "any separate broker-integration work. This page itself never submits orders."
)
