"""Forex Lab: pair overview, currency strength, FX backtests and position sizing (research only)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.strategy_lab import STRATEGIES
from forex.analytics import correlation_matrix, currency_strength, pair_overview
from forex.backtest import compare_fx_strategies, run_fx_backtest
from forex.instruments import (
    ALL_PAIRS,
    INR_PAIRS,
    MAJORS,
    margin_required,
    position_size,
    yahoo_symbol,
)
from services.cached_download import cached_download

st.set_page_config(page_title="Forex Lab", page_icon="💱", layout="wide")
st.title("💱 Forex Lab")
st.warning(
    "RESEARCH ONLY — no orders are placed. Leveraged FX can lose more than expected. Indian "
    "residents are generally limited by FEMA/RBI rules to INR pairs (USDINR, EURINR, GBPINR, "
    "JPYINR) on recognised exchanges, and trading unauthorised offshore platforms is "
    "restricted. Check the rules and your broker before trading."
)


@st.cache_data(ttl=600, show_spinner=False)
def _closes(pairs: tuple[str, ...], period: str) -> pd.DataFrame:
    raw = cached_download([yahoo_symbol(p) for p in pairs], period=period, progress=False)
    if raw is None or raw.empty or not isinstance(raw.columns, pd.MultiIndex):
        return pd.DataFrame()
    close = raw["Close"].dropna(how="all")
    close.columns = [str(c).replace("=X", "") for c in close.columns]
    return close


@st.cache_data(ttl=600, show_spinner=False)
def _ohlc(pair: str, period: str) -> pd.DataFrame | None:
    raw = cached_download(yahoo_symbol(pair), period=period, progress=False)
    if raw is None or raw.empty:
        return None
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    return raw


tab_over, tab_bt, tab_size = st.tabs(["Market overview", "Backtest", "Position size"])

with tab_over:
    chosen = st.multiselect("Pairs", list(ALL_PAIRS), default=list(MAJORS[:5]) + ["USDINR"])
    if st.button("Load market", type="primary") and chosen:
        close = _closes(tuple(chosen), "2y")
        if close.empty:
            st.error("No FX data came back. Try again shortly.")
        else:
            try:
                st.dataframe(
                    pair_overview(close).style.format(
                        {
                            "Last": "{:.4f}",
                            "1D": "{:.2%}",
                            "1M": "{:.2%}",
                            "3M": "{:.2%}",
                            "Annual vol": "{:.1%}",
                        }
                    ),
                    use_container_width=True,
                )
                st.markdown("**Currency strength (20-day)**")
                st.line_chart(currency_strength(close, 20).dropna(how="all").tail(250))
                st.markdown("**Return correlation (last 120 days)**")
                st.dataframe(
                    correlation_matrix(close, 120).style.format("{:.2f}"), use_container_width=True
                )
            except ValueError as exc:
                st.error(str(exc))

with tab_bt:
    c1, c2 = st.columns(2)
    with c1:
        pair = st.selectbox("Pair", list(ALL_PAIRS), index=len(MAJORS) + 5)
        period = st.selectbox("History", ["5y", "10y"], index=0)
        strategy = st.selectbox("Strategy", STRATEGIES)
        allow_short = st.checkbox("Allow short positions", value=True)
    with c2:
        spread = st.number_input("Spread (pips, per round trip)", 0.0, 50.0, 1.5, 0.1)
        base_rate = (
            st.number_input("Base-currency interest rate (% a year)", -5.0, 30.0, 0.0, 0.25) / 100
        )
        quote_rate = (
            st.number_input("Quote-currency interest rate (% a year)", -5.0, 30.0, 0.0, 0.25) / 100
        )
        leverage = st.slider("Leverage", 1, 20, 1)
        st.caption(
            "Enter current policy rates yourself; carry is the rate difference only, "
            "before your broker's swap markup. Spread varies by broker and time of day."
        )
    if st.button("Run FX backtest", type="primary"):
        frame = _ohlc(pair, period)
        if frame is None:
            st.error(f"No data for {pair}.")
        else:
            try:
                kw = {
                    "spread_pips": float(spread),
                    "base_rate": base_rate,
                    "quote_rate": quote_rate,
                    "allow_short": allow_short,
                    "leverage": float(leverage),
                }
                res = run_fx_backtest(frame, pair, strategy, **kw)
                table = compare_fx_strategies(frame, pair, STRATEGIES, **kw)
            except ValueError as exc:
                st.error(str(exc))
                st.stop()
            m = res.metrics
            cols = st.columns(5)
            cols[0].metric("Return", f"{m['total_return']:.1%}")
            cols[1].metric("CAGR", f"{m['cagr']:.1%}")
            cols[2].metric("Sharpe", f"{m['sharpe']:.2f}")
            cols[3].metric("Max drawdown", f"{m['max_drawdown']:.1%}")
            cols[4].metric("Trades", res.trades, f"carry {res.carry_return.sum():.1%}")
            st.line_chart(res.curve[["net_equity"]])
            st.markdown("**All strategies, same settings**")
            st.dataframe(
                table.style.format(
                    {
                        "total_return": "{:.1%}",
                        "cagr": "{:.1%}",
                        "volatility": "{:.1%}",
                        "sharpe": "{:.2f}",
                        "max_drawdown": "{:.1%}",
                        "carry earned": "{:.1%}",
                    }
                ),
                use_container_width=True,
            )
            if leverage > 1:
                st.caption(
                    "Leverage scales returns on the notional; margin calls and stop-outs are not simulated."
                )

with tab_size:
    c1, c2 = st.columns(2)
    with c1:
        sp = st.selectbox("Pair to size", list(ALL_PAIRS), key="size_pair")
        balance = st.number_input("Account balance", 1_000.0, value=1_000_000.0, step=10_000.0)
        risk = st.slider("Risk per trade (%)", 0.1, 5.0, 1.0, 0.1) / 100
    with c2:
        stop = st.number_input("Stop distance (pips)", 1.0, 2000.0, 50.0, 1.0)
        qrate = st.number_input(
            "Account currency per 1 unit of the QUOTE currency",
            0.0001,
            value=1.0,
            format="%.4f",
            help="Example: INR account, EURUSD -> USDINR rate; USD account, EURUSD -> 1.",
        )
        brate = st.number_input(
            "Account currency per 1 unit of the BASE currency (for notional)",
            0.0001,
            value=1.0,
            format="%.4f",
        )
        lev = st.slider("Broker leverage", 1, 50, 10)
    try:
        ps = position_size(
            sp,
            account_balance=balance,
            risk_pct=risk,
            stop_pips=stop,
            quote_to_account=qrate,
            base_to_account=brate,
        )
        st.metric("Position", f"{ps.units:,.0f} units", f"{ps.lots:.2f} standard lots")
        st.caption(
            f"One pip ≈ {ps.pip_value_account:,.2f} in account currency; loss at the stop ≈ {ps.risk_amount:,.0f}. "
            f"Notional ≈ {ps.notional_account:,.0f}; margin at {lev}× ≈ {margin_required(ps.notional_account, lev):,.0f}. "
            "Slippage and gaps can make the real loss larger."
        )
        if sp in INR_PAIRS:
            st.info(
                "NSE currency futures use fixed contract sizes (e.g. 1,000 USD for USDINR) and a 0.0025 tick; "
                "confirm contract specifications with NSE before sizing."
            )
    except ValueError as exc:
        st.error(str(exc))
