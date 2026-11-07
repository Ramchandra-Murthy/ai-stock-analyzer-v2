"""Streamlit page for AI signal outcome history research."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.benchmark_coverage import summarize_benchmark_coverage
from ai_trading.historical_benchmarks import (
    NIFTY_50_TICKER,
    SECTOR_INDEX_TICKERS,
    attach_historical_benchmarks,
)
from ai_trading.signal_history import attach_horizon_outcomes, summarize_outcomes
from ai_trading.signal_history_store import (
    SignalHistoryStoreError,
    load_signal_snapshot,
    save_signal_snapshot,
    signal_history_backend,
)
from ai_trading.signal_performance import summarize_signal_performance
from ai_trading.signal_trade_evaluation import (
    evaluate_signal_trades,
    summarize_signal_trade_evaluation,
)
from algorithmic_trading.trading_costs import india_cost_model
from components.disclaimer import show_disclaimer
from services.resilient_market_data import download_symbol_frames

st.set_page_config(page_title="AI Signal History", page_icon="🗂️", layout="wide")

st.title("🗂️ AI Signal History")
show_disclaimer()
st.caption("Historical AI signal outcome analytics. No broker orders are submitted.")

if not st.session_state.get("ai_signal_store_loaded", False):
    try:
        stored_records, stored_history = load_signal_snapshot()
        st.session_state["ai_signal_records"] = stored_records
        st.session_state["ai_signal_history"] = stored_history
    except SignalHistoryStoreError as exc:
        st.warning(f"Persistent signal history is unavailable: {exc}")
        st.session_state.setdefault("ai_signal_records", [])
    st.session_state["ai_signal_store_loaded"] = True

st.caption(f"Signal history storage: {signal_history_backend().upper()}")
records = st.session_state.get("ai_signal_records", [])
if not isinstance(records, list):
    records = []
existing_history = st.session_state.get("ai_signal_history")
has_pending_outcomes = (
    not isinstance(existing_history, pd.DataFrame)
    or len(existing_history) < len(records)
    or "completed" not in existing_history.columns
    or not bool(existing_history["completed"].fillna(False).all())
)
refresh_requested = False
if records:
    if has_pending_outcomes and not st.session_state.get("ai_signal_auto_refresh_attempted", False):
        refresh_requested = True
        st.session_state["ai_signal_auto_refresh_attempted"] = True
        st.caption("Automatically checking pending signal outcomes on this visit.")
    if st.button("Refresh completed signal outcomes"):
        refresh_requested = True

if refresh_requested:
    tickers_by_key = {}
    for record in records:
        suffix = ".NS" if record.exchange == "NSE" else ".BO"
        ticker = (
            record.symbol if record.symbol.endswith((".NS", ".BO")) else f"{record.symbol}{suffix}"
        )
        tickers_by_key[f"{record.exchange}:{record.symbol}"] = ticker
    tickers = sorted(set(tickers_by_key.values()))
    with st.spinner(f"Checking {len(tickers)} symbols for completed outcomes..."):
        frames_by_ticker, diagnostics = download_symbol_frames(
            tickers,
            period="5y",
            interval="1d",
            auto_adjust=False,
            batch_size=10,
            timeout=15,
        )
        frames_by_key = {
            key: frames_by_ticker.get(ticker, pd.DataFrame())
            for key, ticker in tickers_by_key.items()
        }
        history = attach_horizon_outcomes(records, frames_by_key)
        st.session_state["ai_signal_history"] = history
        try:
            save_signal_snapshot(records, history)
        except SignalHistoryStoreError as exc:
            st.warning(f"Outcomes were refreshed in this session but could not be persisted: {exc}")
    completed_count = int(history["completed"].sum()) if not history.empty else 0
    st.success(f"Updated signal outcomes: {completed_count}/{len(history)} horizons completed.")
    missing = diagnostics.get("missing", [])
    if missing:
        st.warning(
            f"Market data was unavailable for {len(missing)} symbols; those outcomes remain pending."
        )

history = st.session_state.get("ai_signal_history")

if not isinstance(history, pd.DataFrame) or history.empty:
    st.info(
        "No signal history has been recorded yet. Run the AI Trading Scanner "
        "and use its signal records to populate this research ledger."
    )
    st.stop()

# Backfill market movement for legacy outcome rows that predate this field.
if "market_return_pct" not in history.columns:
    history["market_return_pct"] = pd.NA
market_returns = pd.to_numeric(history["market_return_pct"], errors="coerce")
missing_market_returns = market_returns.isna()
if missing_market_returns.any() and {"entry_price", "outcome_price"}.issubset(history.columns):
    if "adjusted_entry_price" in history:
        entry = pd.to_numeric(history["adjusted_entry_price"], errors="coerce")
    else:
        entry = pd.Series(float("nan"), index=history.index)
    entry = entry.fillna(pd.to_numeric(history["entry_price"], errors="coerce"))
    outcome = pd.to_numeric(history["outcome_price"], errors="coerce")
    valid_prices = (
        missing_market_returns
        & entry.map(lambda value: pd.notna(value) and value > 0.0)
        & outcome.map(lambda value: pd.notna(value) and value > 0.0)
    )
    computed_market_returns = pd.Series(float("nan"), index=history.index)
    computed_market_returns.loc[valid_prices] = (
        outcome.loc[valid_prices] / entry.loc[valid_prices] - 1.0
    ) * 100.0
    history.loc[valid_prices, "market_return_pct"] = computed_market_returns.loc[valid_prices]
neutral_mask = history["signal"].eq("NEUTRAL")
history.loc[neutral_mask, "return_pct"] = float("nan")

st.subheader("Historical Benchmark Comparison")
st.caption(
    "Matches each signal to NIFTY 50 and, where mapped, its NIFTY sector index. "
    "Intraday signals use the previous completed daily close; after-close signals "
    "may use that session close. The outcome benchmark must have an exact matching "
    "session. Missing data remains unavailable, not estimated."
)
if "outcome_timestamp" not in history.columns:
    st.info(
        "Benchmark matching requires recorded outcome timestamps. Refresh signal outcomes first."
    )
elif st.button("Refresh historical benchmark returns"):
    benchmark_tickers = list(dict.fromkeys([NIFTY_50_TICKER, *SECTOR_INDEX_TICKERS.values()]))
    with st.spinner("Downloading NIFTY 50 and sector-index history..."):
        benchmark_frames, benchmark_diagnostics = download_symbol_frames(
            benchmark_tickers,
            period="5y",
            interval="1d",
            auto_adjust=False,
            batch_size=10,
            timeout=15,
        )
        history = attach_historical_benchmarks(history, benchmark_frames)
        st.session_state["ai_signal_history"] = history
        try:
            save_signal_snapshot(records, history)
        except SignalHistoryStoreError as exc:
            st.warning(
                f"Benchmark results are available in this session but could not be persisted: {exc}"
            )
    matched = int(history["benchmark_status"].eq("matched_daily_close_proxy").sum())
    st.success(f"Matched NIFTY 50 returns for {matched}/{len(history)} signal observations.")
    missing_benchmarks = benchmark_diagnostics.get("missing", [])
    if missing_benchmarks:
        st.warning(
            f"Yahoo Finance did not return {len(missing_benchmarks)} benchmark indices. "
            "Those comparisons remain unavailable."
        )

if "benchmark_return_pct" in history.columns:
    st.subheader("Benchmark Data Coverage")
    coverage = summarize_benchmark_coverage(history)
    st.dataframe(coverage, use_container_width=True, hide_index=True)
    st.caption(
        "Coverage is matched observations divided by eligible observations. NIFTY 50 "
        "uses all signal observations; sector coverage excludes symbols without a "
        "curated sector-index mapping. Status breakdowns explain unmatched records. "
        "Matched values are daily-close proxies, not exact intraday benchmark prices."
    )
    benchmark_columns = [
        column
        for column in (
            "symbol",
            "timestamp",
            "outcome_timestamp",
            "benchmark_name",
            "benchmark_return_pct",
            "benchmark_status",
            "sector",
            "sector_benchmark_name",
            "sector_benchmark_return_pct",
            "sector_benchmark_status",
        )
        if column in history.columns
    ]
    st.dataframe(history[benchmark_columns], use_container_width=True, hide_index=True)
    st.download_button(
        "Download Historical Benchmark Report CSV",
        data=history[benchmark_columns].to_csv(index=False).encode("utf-8"),
        file_name="historical_signal_benchmarks.csv",
        mime="text/csv",
    )

st.subheader("Signal History")
st.dataframe(history, use_container_width=True, hide_index=True)

summary = summarize_outcomes(history)
if summary.empty:
    st.info("No completed signal outcomes are available yet.")
else:
    st.subheader("Outcome Summary")
    st.dataframe(summary, use_container_width=True, hide_index=True)

st.subheader("Signal Performance & Reliability")
performance = summarize_signal_performance(history)
if performance.empty:
    st.info("Performance metrics require completed outcomes with valid returns.")
else:
    st.caption(
        "Only completed outcomes are included. Break-even results count in the sample, "
        "but are neither wins nor losses. Win-rate bounds are 95% Wilson intervals. "
        "Drawdown is an equally weighted sequential signal-return proxy, not account-level "
        "drawdown; overlapping positions, brokerage, taxes and slippage are not modeled."
    )
    st.dataframe(performance, use_container_width=True, hide_index=True)
    st.download_button(
        "Download Performance Report CSV",
        data=performance.to_csv(index=False).encode("utf-8"),
        file_name="signal_performance_report.csv",
        mime="text/csv",
    )

st.subheader("Cost-Adjusted Trade Evaluation")
st.caption(
    "Estimates one entry and one exit for each completed directional signal. "
    "Costs use configurable NSE equity assumptions; this is not a fill-level or "
    "portfolio backtest. Short cash-equity signals may not be held overnight in India."
)
cost_product_col, cost_slippage_col, cost_brokerage_col = st.columns(3)
cost_product = cost_product_col.selectbox(
    "Equity product assumption",
    options=["delivery", "intraday"],
    format_func=lambda value: "Delivery" if value == "delivery" else "Intraday",
)
cost_slippage = cost_slippage_col.number_input(
    "Slippage (bps per side)",
    min_value=0.0,
    max_value=200.0,
    value=5.0,
    step=1.0,
)
default_brokerage = 0.0 if cost_product == "delivery" else 3.0
cost_brokerage = cost_brokerage_col.number_input(
    "Brokerage (bps per side)",
    min_value=0.0,
    max_value=100.0,
    value=default_brokerage,
    step=0.5,
)
cost_model = india_cost_model(
    cost_product,
    brokerage_bps=cost_brokerage,
    slippage_bps=cost_slippage,
)
trade_evaluation = evaluate_signal_trades(history, cost_model)
trade_summary = summarize_signal_trade_evaluation(trade_evaluation)
if trade_summary.empty:
    st.info("Cost-adjusted metrics require completed LONG or SHORT outcomes.")
else:
    st.dataframe(trade_summary, use_container_width=True, hide_index=True)
    st.download_button(
        "Download Cost-Adjusted Trade Report CSV",
        data=trade_evaluation.to_csv(index=False).encode("utf-8"),
        file_name="cost_adjusted_signal_trades.csv",
        mime="text/csv",
    )
    if trade_evaluation["excess_return_pct"].notna().any():
        st.caption(
            "NIFTY 50 excess is direction-adjusted and shown only where a matching "
            "benchmark observation exists. Sector excess is calculated separately "
            "where a mapped sector-index observation is available. Both are measured "
            "against net returns after estimated costs."
        )
    else:
        st.caption(
            "Benchmark comparison is pending matching benchmark-return observations; "
            "no benchmark performance is inferred or fabricated. Sector-relative "
            "metrics also remain unavailable until a mapped sector index is matched."
        )

completed = history.loc[history["completed"].fillna(False)].copy()
directional = completed.loc[pd.to_numeric(completed["return_pct"], errors="coerce").notna()]
metric1, metric2, metric3 = st.columns(3)
metric1.metric("Signals", len(history))
metric2.metric("Completed outcomes", len(completed))
metric3.metric(
    "Average directional return",
    f"{directional['return_pct'].mean():.2f}%" if not directional.empty else "N/A",
)

neutral = completed.loc[completed["signal"].eq("NEUTRAL")]
if not neutral.empty and "market_return_pct" in neutral.columns:
    neutral_returns = pd.to_numeric(neutral["market_return_pct"], errors="coerce").dropna()
    if not neutral_returns.empty:
        st.info(
            f"Neutral signals are not treated as trades. Their underlying stocks averaged "
            f"{neutral_returns.mean():+.2f}% over the recorded horizon "
            f"({len(neutral_returns)} completed observations)."
        )

st.subheader("Completed Directional Signal Returns")
if directional.empty:
    st.info("Directional return charts will appear when completed LONG or SHORT outcomes exist.")
else:
    st.bar_chart(directional.set_index("symbol")["return_pct"])

csv = history.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Signal History CSV",
    data=csv,
    file_name="ai_signal_history.csv",
    mime="text/csv",
)

st.caption(
    "Outcome returns are historical measurements based on supplied outcome prices. "
    "They are not forecasts or guarantees of future performance."
)
