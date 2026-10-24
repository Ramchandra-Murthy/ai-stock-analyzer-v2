"""Strategy Lab: backtest the systematic strategy library on any NSE or BSE stock."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.regime_filter import REGIME_MODES, regime_gate, regime_share
from algorithmic_trading.strategy_lab import (
    STRATEGIES,
    compare_strategies,
    normalise_price_frame,
    run_strategy_lab,
)
from algorithmic_trading.trading_costs import RATES_VERIFIED, india_cost_model, round_trip_bps
from services.resilient_market_data import download_market_frames

st.set_page_config(page_title="Strategy Lab", page_icon="🧪", layout="wide")

st.title("🧪 Strategy Lab")
st.warning(
    "RESEARCH ONLY — historical backtests are not forecasts and this page never places "
    "orders. Results ignore slippage beyond the cost you enter, taxes and liquidity limits."
)
st.caption(
    "Trend (Supertrend), breakout (Donchian), mean reversion (z-score, RSI(2)) and an "
    "ensemble vote. A signal on one bar is traded on the next, so there is no look-ahead."
)


@st.cache_data(ttl=300, show_spinner=False)
def _load_prices(ticker: str, period: str) -> tuple[pd.DataFrame | None, str]:
    frames, diagnostics = download_market_frames([ticker], period=period, interval="1d")
    frame = frames.get(ticker.upper())
    if frame is None or frame.empty:
        return None, f"No data returned for {ticker}. Missing: {diagnostics.get('missing')}"
    return frame, ""


def _pct(value: float | None) -> str:
    return "n/a" if value is None or pd.isna(value) else f"{value:.1%}"


left, right = st.columns(2)
with left:
    exchange = st.selectbox("Exchange", ["NSE", "BSE"])
    symbol = st.text_input(
        "Symbol", "RELIANCE", help="NSE symbol (RELIANCE) or BSE scrip name/code (500325)."
    )
    period = st.selectbox("History", ["2y", "5y", "10y"], index=1)
    strategy = st.selectbox("Strategy", STRATEGIES, index=len(STRATEGIES) - 1)
with right:
    capital = st.number_input("Initial capital (₹)", 1_000.0, value=100_000.0, step=10_000.0)
    cost_choice = st.radio(
        "Trading costs",
        ["Flat per-trade cost", "NSE delivery (statutory rates)", "NSE intraday (statutory rates)"],
        help="The NSE presets use STT, stamp duty, exchange, SEBI and GST rates; "
        f"verified {RATES_VERIFIED}. Re-check them and your broker's brokerage.",
    )
    cost_bps = 10.0
    cost_model = None
    if cost_choice == "Flat per-trade cost":
        cost_bps = st.number_input(
            "Cost per trade, each side (bps of traded value)", 0.0, 500.0, 10.0, 1.0
        )
    else:
        brokerage = st.number_input(
            "Brokerage per side (bps)",
            0.0,
            50.0,
            0.0 if "delivery" in cost_choice else 3.0,
            0.5,
            help="Your broker's real figure. Delivery is often free at discount brokers.",
        )
        slippage = st.number_input(
            "Slippage per side (bps)", 0.0, 100.0, 5.0, 0.5, help="An assumption, not a rate."
        )
        cost_model = india_cost_model(
            "delivery" if "delivery" in cost_choice else "intraday",
            brokerage_bps=float(brokerage),
            slippage_bps=float(slippage),
        )
        st.caption(
            f"Estimated round-trip cost: {round_trip_bps(cost_model):.1f} bps of traded value"
        )
    allow_short = st.checkbox(
        "Allow short positions",
        value=False,
        help="Cash-market delivery shorting is not available to retail investors in India.",
    )
    regime_choice = st.selectbox(
        "Market regime filter",
        ["None", *REGIME_MODES],
        help="Stand aside when the regime is unfavourable. Uses only past data. It usually "
        "trades a smaller drawdown for lower return; the comparison below shows both.",
    )
    use_vol_target = st.checkbox("Volatility targeting", value=False)
    target_vol = (
        st.slider("Target annual volatility", 0.05, 0.40, 0.15, 0.01) if use_vol_target else None
    )

run = st.button("Run backtest", type="primary")

if run:
    symbol = symbol.strip().upper()
    if not symbol:
        st.error("Enter a symbol.")
        st.stop()
    ticker = f"{symbol}.{'NS' if exchange == 'NSE' else 'BO'}"

    with st.spinner(f"Loading {ticker}..."):
        raw, error = _load_prices(ticker, period)
    if raw is None:
        st.error(error)
        st.stop()

    try:
        prices = normalise_price_frame(raw)
        gate = None if regime_choice == "None" else regime_gate(prices["Close"], regime_choice)
        result = run_strategy_lab(
            prices,
            strategy,
            capital=float(capital),
            cost_bps=float(cost_bps),
            cost_model=cost_model,
            allow_short=allow_short,
            target_volatility=target_vol,
            regime=gate,
        )
        ungated = (
            None
            if gate is None
            else run_strategy_lab(
                prices,
                strategy,
                capital=float(capital),
                cost_bps=float(cost_bps),
                cost_model=cost_model,
                allow_short=allow_short,
                target_volatility=target_vol,
            )
        )
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    m = result.metrics
    st.subheader(f"{ticker} — {strategy}")
    cols = st.columns(5)
    cols[0].metric(
        "Strategy return", _pct(m.total_return), f"vs buy & hold {_pct(m.buy_hold_return)}"
    )
    cols[1].metric("CAGR", _pct(m.cagr))
    cols[2].metric("Max drawdown", _pct(m.max_drawdown))
    cols[3].metric("Sharpe", "n/a" if m.sharpe_ratio is None else f"{m.sharpe_ratio:.2f}")
    cols[4].metric("Trades", m.trade_count, f"win rate {_pct(m.win_rate)}")

    st.markdown("**Equity curve**")
    equity = result.curve[["strategy_equity", "buy_hold_equity"]]
    if ungated is not None and gate is not None:
        equity = equity.assign(without_filter=ungated.curve["strategy_equity"])
    st.line_chart(equity)
    if ungated is not None and gate is not None:
        u = ungated.metrics
        st.caption(
            f"Regime filter ({regime_choice}) was on {regime_share(gate):.0%} of bars. "
            f"With filter: return {_pct(m.total_return)}, max drawdown {_pct(m.max_drawdown)}, "
            f"Sharpe {'n/a' if m.sharpe_ratio is None else f'{m.sharpe_ratio:.2f}'}. "
            f"Without: return {_pct(u.total_return)}, max drawdown {_pct(u.max_drawdown)}, "
            f"Sharpe {'n/a' if u.sharpe_ratio is None else f'{u.sharpe_ratio:.2f}'}."
        )
    st.markdown("**Drawdown**")
    st.area_chart(result.curve["drawdown"])

    st.markdown("**All strategies on the same data**")
    table = compare_strategies(
        prices,
        capital=float(capital),
        cost_bps=float(cost_bps),
        cost_model=cost_model,
        allow_short=allow_short,
    )
    if table.empty:
        st.info("Not enough history to compare strategies.")
    else:
        st.dataframe(
            table.style.format(
                {
                    "Total return": "{:.1%}",
                    "CAGR": "{:.1%}",
                    "Max drawdown": "{:.1%}",
                    "Sharpe": "{:.2f}",
                    "Win rate": "{:.0%}",
                    "Buy & hold": "{:.1%}",
                },
                na_rep="n/a",
            ),
            hide_index=True,
            use_container_width=True,
        )
    st.caption(
        "Picking the best row after seeing it is itself a form of overfitting: treat the "
        "winner as a hypothesis to validate on other stocks and periods, not as proof."
    )
