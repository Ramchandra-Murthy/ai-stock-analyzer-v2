"""Streamlit page for AI paper trading."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.ml_scanner import scan_universe
from ai_trading.paper_trading import PaperPortfolio, apply_ml_signals
from ai_trading.risk import RiskLimits, risk_warnings
from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES
from components.disclaimer import show_disclaimer
from services.cached_download import cached_download

st.set_page_config(
    page_title="AI Paper Trading",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 AI Paper Trading")
show_disclaimer()
st.caption(
    "Simulation only. ML signals are converted into paper fills and portfolio "
    "positions; no broker orders are submitted."
)

if "ai_paper_portfolio" not in st.session_state:
    st.session_state.ai_paper_portfolio = PaperPortfolio(initial_cash=100_000.0)

portfolio = st.session_state.ai_paper_portfolio

left, mid, right = st.columns(3)
with left:
    exchange = st.selectbox("Exchange", ["NSE", "BSE"])
    universe = NSE_CANDIDATES if exchange == "NSE" else BSE_CANDIDATES
    count = st.slider(
        "ML symbols",
        5,
        min(30, len(universe)),
        min(10, len(universe)),
        5,
    )
with mid:
    horizon = st.slider("ML horizon (days)", 1, 20, 5)
    threshold = st.slider("ML threshold (%)", 0.0, 5.0, 1.0, 0.5)
with right:
    capital_fraction = st.slider("Capital per cycle", 0.05, 1.0, 0.20, 0.05)
    max_positions = st.slider("Max positions", 1, 10, 5)

st.subheader("Risk controls")
risk1, risk2, risk3 = st.columns(3)
with risk1:
    max_exposure_pct = st.slider("Max portfolio exposure", 20.0, 100.0, 80.0, 5.0)
with risk2:
    max_position_pct = st.slider("Max position size", 5.0, 50.0, 20.0, 5.0)
with risk3:
    cash_reserve_pct = st.slider("Minimum cash reserve", 0.0, 50.0, 10.0, 5.0)

risk_limits = RiskLimits(
    max_exposure_pct=max_exposure_pct,
    max_position_pct=max_position_pct,
    cash_reserve_pct=cash_reserve_pct,
)

if st.button("Run AI Paper Trading Cycle", type="primary"):
    with st.spinner(f"Training {count} {exchange} ML models..."):
        result = scan_universe(
            universe[:count],
            exchange=exchange,
            period="5y",
            horizon=horizon,
            threshold=threshold / 100.0,
        )

    if result.empty:
        st.warning("No valid ML signals were produced.")
        st.stop()

    tickers = [
        (
            f"{str(symbol).strip().upper()}.NS"
            if exchange == "NSE"
            else f"{str(symbol).strip().upper()}.BO"
        )
        for symbol in result["symbol"]
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
        for symbol, ticker in zip(result["symbol"], tickers, strict=True):
            if ticker in close_data:
                series = pd.to_numeric(close_data[ticker], errors="coerce").dropna()
                if not series.empty:
                    prices[str(symbol).upper()] = float(series.iloc[-1])
    elif "Close" in prices_data:
        series = pd.to_numeric(prices_data["Close"], errors="coerce").dropna()
        if not series.empty and len(result) == 1:
            prices[str(result.iloc[0]["symbol"]).upper()] = float(series.iloc[-1])

    fills = apply_ml_signals(
        portfolio,
        result,
        prices,
        capital_fraction=capital_fraction,
        max_positions=max_positions,
        risk_limits=risk_limits,
    )
    st.session_state.ai_paper_scan = result
    st.session_state.ai_paper_prices = prices
    portfolio.record_equity(prices)

    st.success(f"Completed paper cycle: {len(fills)} simulated fills.")

scan = st.session_state.get("ai_paper_scan")
prices = st.session_state.get("ai_paper_prices", {})

if scan is not None and not scan.empty:
    st.subheader("Latest ML signals")
    st.dataframe(scan.head(10), use_container_width=True, hide_index=True)

equity = portfolio.equity(prices)
market_value = sum(
    quantity * float(prices[symbol])
    for symbol, quantity in portfolio.positions.items()
    if symbol in prices
)
warnings = risk_warnings(equity, portfolio.cash, market_value, risk_limits)
for warning in warnings:
    st.warning(warning)

risk_metrics = st.columns(3)
risk_metrics[0].metric(
    "Exposure",
    f"{market_value / equity * 100.0:.1f}%" if equity > 0 else "0.0%",
)
risk_metrics[1].metric("Cash reserve", f"₹{portfolio.cash:,.2f}")
risk_metrics[2].metric("Risk cap", f"{risk_limits.max_exposure_pct:.0f}%")

metric1, metric2, metric3, metric4 = st.columns(4)
metric1.metric("Paper equity", f"₹{equity:,.2f}")
metric2.metric("Cash", f"₹{portfolio.cash:,.2f}")
metric3.metric("Open positions", len(portfolio.positions))
metric4.metric("Simulated fills", len(portfolio.trades))

st.subheader("Open positions")
if portfolio.positions:
    position_rows = [
        {
            "symbol": symbol,
            "quantity": quantity,
            "price": prices.get(symbol),
            "market_value": quantity * prices[symbol] if symbol in prices else None,
        }
        for symbol, quantity in portfolio.positions.items()
    ]
    st.dataframe(position_rows, use_container_width=True, hide_index=True)
else:
    st.info("No open paper positions.")

st.subheader("Paper trade journal")
if portfolio.trades:
    st.dataframe(
        [
            {
                "symbol": trade.symbol,
                "side": trade.side,
                "quantity": trade.quantity,
                "price": trade.price,
                "value": trade.value,
                "cash_after": trade.cash_after,
                "signal": trade.signal,
                "confidence_pct": trade.confidence_pct,
                "reason": trade.reason,
                "timestamp": trade.timestamp.isoformat(),
            }
            for trade in portfolio.trades
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No simulated fills yet.")

if st.button("Reset AI Paper Portfolio"):
    st.session_state.ai_paper_portfolio = PaperPortfolio(initial_cash=100_000.0)
    st.session_state.pop("ai_paper_scan", None)
    st.session_state.pop("ai_paper_prices", None)
    st.rerun()
