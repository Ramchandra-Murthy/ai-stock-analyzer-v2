"""Crypto Lab: risk, backtests with fees and Indian VDA tax, DCA and perpetual-futures maths."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.strategy_lab import STRATEGIES
from crypto.analytics import (
    correlation,
    dca_simulation,
    funding_cost,
    liquidation_price,
    position_size,
    risk_overview,
)
from crypto.backtest import compare_crypto_strategies, run_crypto_backtest
from crypto.instruments import COINS, INR_QUOTED, FeeModel, yahoo_symbol
from services.cached_download import cached_download

st.set_page_config(page_title="Crypto Lab", page_icon="🪙", layout="wide")
st.title("🪙 Crypto Lab")
st.warning(
    "RESEARCH ONLY — no exchange connection, no orders. Crypto is extremely volatile, largely "
    "unregulated in India, and exposed to exchange failure and scams. In India, gains are taxed "
    "at a flat 30% (+4% cess) with no set-off of losses and 1% TDS on transfers; rules change, "
    "so confirm with a chartered accountant."
)


@st.cache_data(ttl=600, show_spinner=False)
def _ohlc(symbol: str, period: str) -> pd.DataFrame | None:
    raw = cached_download(symbol, period=period, progress=False)
    if raw is None or raw.empty:
        return None
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    return raw


@st.cache_data(ttl=600, show_spinner=False)
def _closes(symbols: tuple[str, ...], period: str) -> pd.DataFrame:
    raw = cached_download(list(symbols), period=period, progress=False)
    if raw is None or raw.empty or not isinstance(raw.columns, pd.MultiIndex):
        return pd.DataFrame()
    return raw["Close"].dropna(how="all")


tab_mkt, tab_bt, tab_tools = st.tabs(["Market risk", "Backtest", "DCA & derivatives tools"])

with tab_mkt:
    coins = st.multiselect("Coins", list(COINS), default=list(COINS[:5]))
    if st.button("Load", type="primary") and coins:
        close = _closes(tuple(yahoo_symbol(c) for c in coins), "5y")
        if close.empty:
            st.error("No crypto data came back. Try again shortly.")
        else:
            rows = {}
            for col in close.columns:
                try:
                    rows[str(col).replace("-USD", "")] = risk_overview(close[col].dropna())
                except ValueError:
                    continue
            if rows:
                st.dataframe(pd.DataFrame(rows).T.style.format("{:.1%}"), use_container_width=True)
            try:
                st.markdown("**Return correlation (last 180 days)** — coins tend to fall together")
                st.dataframe(
                    correlation(close, 180).style.format("{:.2f}"), use_container_width=True
                )
            except ValueError as exc:
                st.info(str(exc))

with tab_bt:
    c1, c2 = st.columns(2)
    with c1:
        coin = st.selectbox("Coin", list(COINS))
        quote = st.selectbox(
            "Quote currency",
            ["USD", "INR"],
            help="INR is only available for " + ", ".join(INR_QUOTED),
        )
        period = st.selectbox("History", ["5y", "10y", "max"], index=0)
        strategy = st.selectbox("Strategy", STRATEGIES)
        shorts = st.checkbox("Allow shorts (perpetual futures only)", value=False)
    with c2:
        taker = st.number_input("Exchange fee (bps per side)", 0.0, 200.0, 10.0, 1.0)
        slip = st.number_input("Slippage (bps per side)", 0.0, 200.0, 10.0, 1.0)
        gst = st.checkbox("Add 18% GST on exchange fees (Indian exchanges)", value=True)
    if st.button("Run crypto backtest", type="primary"):
        try:
            frame = _ohlc(yahoo_symbol(coin, quote), period)
            if frame is None:
                raise ValueError(f"No data for {coin}-{quote}.")
            fees = FeeModel(
                taker_bps=taker, maker_bps=taker, slippage_bps=slip, gst_rate=0.18 if gst else 0.0
            )
            res = run_crypto_backtest(frame, strategy, fees=fees, allow_short=shorts)
            table = compare_crypto_strategies(frame, STRATEGIES, fees=fees, allow_short=shorts)
        except ValueError as exc:
            st.error(str(exc))
            st.stop()
        m, t = res.metrics, res.after_tax
        cols = st.columns(5)
        cols[0].metric("Return (pre-tax)", f"{m['total_return']:.1%}")
        cols[1].metric(
            "Return (after VDA tax)",
            f"{t['after_tax_return']:.1%}",
            f"tax ₹/$ {t['tax_paid']:,.0f}",
        )
        cols[2].metric("Sharpe", f"{m['sharpe']:.2f}")
        cols[3].metric("Max drawdown", f"{m['max_drawdown']:.1%}")
        cols[4].metric("Trades", len(res.trade_returns))
        st.line_chart(res.curve[["strategy_equity", "buy_hold_equity"]])
        st.caption(
            f"Round-trip cost assumed: {fees.round_trip_bps():.0f} bps. The after-tax figure applies "
            "30% + cess to each winning trade with no relief for losing trades; it ignores TDS "
            "timing and is an illustration, not tax advice. Buy-and-hold is taxed only on sale."
        )
        st.dataframe(
            table.style.format(
                dict.fromkeys(
                    (
                        "total_return",
                        "cagr",
                        "volatility",
                        "max_drawdown",
                        "after_tax_return",
                        "buy_hold_return",
                    ),
                    "{:.1%}",
                )
                | {"sharpe": "{:.2f}"}
            ),
            use_container_width=True,
        )

with tab_tools:
    st.markdown("**Dollar-cost averaging vs lumpsum**")
    c1, c2, c3 = st.columns(3)
    with c1:
        dca_coin = st.selectbox("Coin", list(COINS), key="dca_coin")
    with c2:
        amount = st.number_input("Amount per buy", 1.0, value=1000.0)
    with c3:
        every = st.selectbox("Every (days)", [1, 7, 14, 30], index=1)
    if st.button("Simulate DCA"):
        frame = _ohlc(yahoo_symbol(dca_coin), "5y")
        if frame is None:
            st.error("No data.")
        else:
            try:
                d = dca_simulation(frame["Close"], float(amount), int(every))
                a, b, c = st.columns(3)
                a.metric("DCA return", f"{d['return']:.1%}")
                b.metric("Lumpsum return", f"{d['lumpsum_return']:.1%}")
                c.metric("Average cost", f"{d['average_cost']:,.2f}")
            except ValueError as exc:
                st.error(str(exc))
    st.markdown("**Perpetual futures: liquidation and funding**")
    c1, c2 = st.columns(2)
    with c1:
        entry = st.number_input("Entry price", 0.0001, value=60_000.0)
        lev = st.slider("Leverage", 1, 50, 5)
        is_long = st.radio("Side", ["Long", "Short"]) == "Long"
    with c2:
        notional = st.number_input("Notional", 1.0, value=10_000.0)
        rate = (
            st.number_input("Funding rate per 8h (%)", -0.5, 0.5, 0.01, 0.005, format="%.3f") / 100
        )
        days = st.number_input("Days held", 0.0, 365.0, 30.0)
    liq = liquidation_price(entry, lev, long=is_long)
    st.metric("Approx. liquidation price", f"{liq:,.2f}", f"{liq / entry - 1:.1%} from entry")
    st.caption(
        f"Funding over {days:g} days: {funding_cost(notional, rate, days, long=is_long):,.2f} "
        "(positive = you pay). Real liquidation happens earlier once fees and tiered margin apply; "
        "crypto can gap through your stop."
    )
    st.markdown("**Position size**")
    bal = st.number_input("Account balance", 1.0, value=10_000.0, key="bal")
    rp = st.slider("Risk per trade (%)", 0.1, 5.0, 1.0, 0.1, key="rp") / 100
    stop = st.number_input("Stop price", 0.0001, value=57_000.0)
    try:
        p = position_size(bal, rp, entry, stop)
        st.metric(
            "Quantity",
            f"{p['quantity']:.6f}",
            f"notional {p['notional']:,.0f}, leverage needed {p['leverage_needed']:.1f}×",
        )
    except ValueError as exc:
        st.error(str(exc))
