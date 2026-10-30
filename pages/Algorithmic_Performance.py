"""Streamlit dashboard for algorithmic trading performance research."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.multi_stock_validation import evaluate_symbol_universe
from algorithmic_trading.signal_backtest import backtest_pipeline, generate_pipeline_signals
from algorithmic_trading.trading_costs import IndiaEquityCostModel
from algorithmic_trading.walk_forward_validation import walk_forward_evaluate
from components.disclaimer import show_disclaimer
from services.resilient_market_data import download_symbol_frames


@st.cache_data(ttl=300, show_spinner=False)
def _download_ticker_data(ticker: str, period: str) -> pd.DataFrame:
    """Cache bounded-retry historical downloads without inventing fallback prices."""
    frames, missing = download_symbol_frames(
        [ticker],
        period=period,
        interval="1d",
        auto_adjust=False,
        batch_size=1,
        timeout=15,
    )
    if missing or ticker not in frames:
        return pd.DataFrame()
    return frames[ticker].copy()


@st.cache_data(ttl=300, show_spinner=False)
def _download_ticker_frames(
    tickers: tuple[str, ...], period: str
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Download a bounded universe in batches and cache the resulting frames."""
    frames, missing = download_symbol_frames(
        tickers,
        period=period,
        interval="1d",
        auto_adjust=False,
        batch_size=10,
        timeout=15,
    )
    return {ticker: frame.copy() for ticker, frame in frames.items()}, missing


def _render_market_data_refresh() -> None:
    """Offer a manual cache invalidation when the user wants a fresh download."""
    if st.button("Refresh cached market data"):
        _download_ticker_data.clear()
        _download_ticker_frames.clear()
        st.success(
            "Cached single-symbol and multi-stock market data cleared. "
            "Run the analysis again to download fresh data."
        )


def _download_market_data(ticker: str, benchmark_ticker: str, period: str):
    """Download and normalize one symbol and its benchmark."""
    with st.spinner(f"Loading {ticker} and {benchmark_ticker}..."):
        frame = _download_ticker_data(ticker, period)
        benchmark = _download_ticker_data(benchmark_ticker, period)

    for data in (frame, benchmark):
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

    return frame, benchmark


def _show_results(data: pd.DataFrame, metrics) -> None:
    """Render the historical backtest results."""
    st.subheader("Historical backtest")
    cols = st.columns(6)
    cols[0].metric("Total return", f"{metrics.total_return:.2%}")
    cols[1].metric("CAGR", f"{metrics.cagr:.2%}" if metrics.cagr is not None else "—")
    cols[2].metric("Max drawdown", f"{metrics.max_drawdown:.2%}")
    cols[3].metric("Buy & hold", f"{metrics.buy_hold_return:.2%}")
    cols[4].metric("Trades", metrics.trade_count)
    cols[5].metric("Win rate", f"{metrics.win_rate:.2%}")

    st.subheader("Risk-adjusted diagnostics")
    st.caption(
        "Annualized from daily strategy returns using 252 trading days. "
        "Sharpe is not adjusted for a risk-free rate; these are historical diagnostics, "
        "not forecasts or guarantees."
    )
    risk_cols = st.columns(4)
    risk_cols[0].metric("Annualized volatility", f"{metrics.volatility:.2%}")
    risk_cols[1].metric(
        "Sharpe ratio",
        f"{metrics.sharpe_ratio:.2f}" if metrics.sharpe_ratio is not None else "—",
    )
    risk_cols[2].metric(
        "Sortino ratio",
        f"{metrics.sortino_ratio:.2f}" if metrics.sortino_ratio is not None else "—",
    )
    risk_cols[3].metric(
        "Calmar ratio",
        f"{metrics.calmar_ratio:.2f}" if metrics.calmar_ratio is not None else "—",
    )

    st.subheader("Equity curve")
    st.line_chart(data[["strategy_equity", "buy_hold_equity"]])

    st.subheader("Drawdown")
    st.line_chart(data["drawdown"])

    st.subheader("Backtest observations")
    st.dataframe(data.tail(250), use_container_width=True)
    st.download_button(
        "Download backtest observations (CSV)",
        data=data.to_csv(index=True).encode("utf-8"),
        file_name="algorithmic_backtest_observations.csv",
        mime="text/csv",
    )


def _run_backtest(
    frame: pd.DataFrame,
    benchmark: pd.DataFrame,
    capital: float,
    cost_bps: float,
    cost_model: IndiaEquityCostModel | None = None,
):
    """Validate data and run the existing point-in-time backtest."""
    if frame.empty or benchmark.empty:
        st.error("No usable historical market data was returned.")
        return None

    if "Close" not in frame.columns or "Close" not in benchmark.columns:
        st.error("Historical data did not contain a usable Close series.")
        return None

    try:
        return backtest_pipeline(
            frame=frame,
            benchmark=benchmark["Close"],
            initial_capital=capital,
            cost_bps=cost_bps,
            cost_model=cost_model,
        )
    except ValueError as exc:
        st.error(str(exc))
        return None


st.set_page_config(
    page_title="NSE/BSE Algorithmic Performance",
    page_icon="📊",
    layout="wide",
)

st.title("📊 NSE/BSE Algorithmic Performance")
show_disclaimer()
_render_market_data_refresh()
st.caption(
    "Historical signal performance only. Open paper positions are not treated " "as realized P&L."
)

left, right = st.columns(2)
with left:
    exchange = st.selectbox("Exchange", ["NSE", "BSE"])
    symbol = st.text_input("Symbol", "RELIANCE").strip().upper()
    period = st.selectbox("History", ["2y", "5y", "10y"], index=0)
with right:
    capital = st.number_input(
        "Initial capital (₹)", min_value=1_000.0, value=100_000.0, step=10_000.0
    )
    cost_bps = st.number_input(
        "Transaction cost (bps)",
        min_value=0.0,
        max_value=500.0,
        value=10.0,
        step=1.0,
    )
    cost_mode = st.radio(
        "Cost model",
        ["Flat cost (bps)", "Itemized India equity"],
        horizontal=True,
    )
    min_train_size = st.number_input(
        "Walk-forward warm-up observations",
        min_value=50,
        max_value=2000,
        value=252,
        step=25,
    )
    n_splits = st.number_input(
        "Walk-forward test windows",
        min_value=2,
        max_value=10,
        value=5,
        step=1,
    )
    run = st.button("Run performance analysis", type="primary")

cost_model = None
if cost_mode == "Itemized India equity":
    st.caption(
        "Enter rates from your broker/exchange tariff for the product and dates "
        "being tested. Values are basis points of traded notional; zero defaults "
        "are placeholders, not estimates of actual charges."
    )
    cost_cols = st.columns(4)
    with cost_cols[0]:
        brokerage_bps = st.number_input("Brokerage (bps)", min_value=0.0, value=0.0, step=0.1)
        exchange_bps = st.number_input(
            "Exchange transaction charges (bps)", min_value=0.0, value=0.0, step=0.1
        )
    with cost_cols[1]:
        regulatory_bps = st.number_input(
            "Regulatory charges (bps)", min_value=0.0, value=0.0, step=0.01
        )
        slippage_bps = st.number_input("Slippage (bps)", min_value=0.0, value=0.0, step=0.1)
    with cost_cols[2]:
        stt_buy_bps = st.number_input("STT buy (bps)", min_value=0.0, value=0.0, step=0.1)
        stt_sell_bps = st.number_input("STT sell (bps)", min_value=0.0, value=0.0, step=0.1)
    with cost_cols[3]:
        stamp_duty_buy_bps = st.number_input(
            "Stamp duty buy (bps)", min_value=0.0, value=0.0, step=0.1
        )
        gst_rate_pct = st.number_input(
            "GST rate (%)", min_value=0.0, max_value=100.0, value=18.0, step=1.0
        )
    cost_model = IndiaEquityCostModel(
        brokerage_bps=brokerage_bps,
        exchange_transaction_bps=exchange_bps,
        regulatory_bps=regulatory_bps,
        stt_buy_bps=stt_buy_bps,
        stt_sell_bps=stt_sell_bps,
        stamp_duty_buy_bps=stamp_duty_buy_bps,
        slippage_bps=slippage_bps,
        gst_rate=gst_rate_pct / 100.0,
    )

if run:
    ticker = f"{symbol}.NS" if exchange == "NSE" else f"{symbol}.BO"
    benchmark_ticker = "^NSEI" if exchange == "NSE" else "^BSESN"
    frame, benchmark = _download_market_data(ticker, benchmark_ticker, period)
    result = _run_backtest(frame, benchmark, capital, cost_bps, cost_model)

    if result is not None:
        data, metrics = result
        _show_results(data, metrics)
        st.subheader("Walk-forward validation")
        st.caption(
            "Sequential test windows evaluate point-in-time signals on later data. "
            "The warm-up is not used for reported fold results. This does not tune "
            "parameters and is not a guarantee of future performance."
        )
        try:
            signals = generate_pipeline_signals(frame, benchmark["Close"])
            prices = pd.to_numeric(frame["Close"], errors="coerce").reindex(signals.index)
            folds = walk_forward_evaluate(
                prices,
                signals,
                initial_capital=capital,
                cost_bps=cost_bps,
                cost_model=cost_model,
                min_train_size=int(min_train_size),
                n_splits=int(n_splits),
            )
            st.dataframe(folds, use_container_width=True)
            st.download_button(
                "Download walk-forward results (CSV)",
                data=folds.to_csv(index=False).encode("utf-8"),
                file_name="walk_forward_validation_results.csv",
                mime="text/csv",
            )
            summary_cols = st.columns(3)
            summary_cols[0].metric("Test windows", len(folds))
            summary_cols[1].metric(
                "Positive-return windows",
                f"{int((folds['total_return'] > 0).sum())}/{len(folds)}",
            )
            summary_cols[2].metric(
                "Median test return",
                f"{folds['total_return'].median():.2%}",
            )
        except ValueError as exc:
            st.warning(f"Walk-forward validation could not run: {exc}")
        st.info(
            "Completed-trade feedback will populate after realized trade records "
            "are connected to the paper-trading ledger."
        )


st.divider()
st.subheader("Multi-stock walk-forward report")
st.caption(
    "Evaluate each symbol independently across sequential out-of-sample windows. "
    "This is not a combined portfolio simulation or a recommendation to buy or sell."
)
universe_text = st.text_input(
    "Symbols (comma-separated)",
    "RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK",
    key="multi_stock_symbols",
)
minimum_observations = st.number_input(
    "Minimum usable observations per symbol",
    min_value=100,
    max_value=3000,
    value=300,
    step=50,
    key="multi_stock_minimum_observations",
)
run_universe = st.button("Run multi-stock validation", type="primary")

if run_universe:
    symbols = list(
        dict.fromkeys(item.strip().upper() for item in universe_text.split(",") if item.strip())
    )
    if not symbols:
        st.error("Enter at least one symbol.")
    elif len(symbols) > 30:
        st.error("Please limit each run to 30 symbols to avoid excessive data requests.")
    else:
        benchmark_ticker = "^NSEI" if exchange == "NSE" else "^BSESN"
        suffix = ".NS" if exchange == "NSE" else ".BO"
        try:
            with st.spinner(f"Downloading benchmark and {len(symbols)} symbols..."):
                benchmark = _download_ticker_data(benchmark_ticker, period)
                if isinstance(benchmark.columns, pd.MultiIndex):
                    benchmark.columns = benchmark.columns.get_level_values(0)
                ticker_map = {item: f"{item}{suffix}" for item in symbols}
                downloaded, missing_tickers = _download_ticker_frames(
                    tuple(ticker_map.values()), period
                )
                frames = {
                    item: downloaded.get(ticker, pd.DataFrame())
                    for item, ticker in ticker_map.items()
                }
                missing_set = set(missing_tickers)
                download_errors = {
                    item: f"no usable historical data returned for {ticker}"
                    for item, ticker in ticker_map.items()
                    if ticker in missing_set
                }
            if benchmark.empty or "Close" not in benchmark.columns:
                st.error("Benchmark data is unavailable; multi-stock validation was not run.")
            else:
                report = evaluate_symbol_universe(
                    frames,
                    benchmark["Close"],
                    initial_capital=capital,
                    cost_bps=cost_bps,
                    cost_model=cost_model,
                    min_train_size=int(min_train_size),
                    n_splits=int(n_splits),
                    minimum_observations=int(minimum_observations),
                )
                for item, reason in download_errors.items():
                    mask = report["symbol"].eq(item) & report["status"].eq("skipped")
                    report.loc[mask, "reason"] = f"Market-data download failed: {reason}"
                if report.empty:
                    st.warning("No validation rows were produced.")
                else:
                    successful = report[report["status"] == "ok"].copy()
                    skipped = report[report["status"] == "skipped"].copy()
                    summary = st.columns(3)
                    summary[0].metric("Symbols requested", len(symbols))
                    summary[1].metric("Symbols evaluated", successful["symbol"].nunique())
                    summary[2].metric("Symbols skipped", skipped["symbol"].nunique())
                    if not skipped.empty:
                        st.caption(
                            "Some symbols were excluded from performance ranking because "
                            "their data or validation history was insufficient."
                        )
                    if not successful.empty:
                        st.subheader("Per-symbol / per-fold results")
                        st.dataframe(successful, use_container_width=True)
                        st.subheader("Symbol summary")
                        summary_frame = successful.groupby("symbol").agg(
                            test_windows=("fold", "count"),
                            positive_windows=(
                                "total_return",
                                lambda values: int((values > 0).sum()),
                            ),
                            median_test_return=("total_return", "median"),
                            median_max_drawdown=("max_drawdown", "median"),
                            median_buy_hold_return=("buy_hold_return", "median"),
                            median_annualized_volatility=("annualized_volatility", "median"),
                            median_sharpe_ratio=("sharpe_ratio", "median"),
                            median_sortino_ratio=("sortino_ratio", "median"),
                            median_calmar_ratio=("calmar_ratio", "median"),
                            sharpe_defined_windows=("sharpe_ratio", "count"),
                            sortino_defined_windows=("sortino_ratio", "count"),
                            calmar_defined_windows=("calmar_ratio", "count"),
                        )
                        summary_frame["positive_window_rate"] = (
                            summary_frame["positive_windows"] / summary_frame["test_windows"]
                        )
                        for metric in ("sharpe", "sortino", "calmar"):
                            summary_frame[f"{metric}_coverage_rate"] = (
                                summary_frame[f"{metric}_defined_windows"]
                                / summary_frame["test_windows"]
                            )
                        sort_options = {
                            "Median test return": "median_test_return",
                            "Median Sharpe ratio": "median_sharpe_ratio",
                            "Median Sortino ratio": "median_sortino_ratio",
                            "Median Calmar ratio": "median_calmar_ratio",
                            "Positive-window rate": "positive_window_rate",
                        }
                        sort_label = st.selectbox(
                            "Rank symbols by",
                            list(sort_options),
                            key="multi_stock_summary_sort",
                        )
                        sort_column = sort_options[sort_label]
                        sorted_summary = summary_frame.sort_values(
                            sort_column, ascending=False, na_position="last"
                        )
                        st.dataframe(sorted_summary, use_container_width=True)
                        summary_csv = sorted_summary.to_csv(index=True, float_format="%.6g").encode(
                            "utf-8"
                        )
                        st.download_button(
                            "Download multi-stock symbol summary (CSV)",
                            data=summary_csv,
                            file_name="multi_stock_symbol_summary.csv",
                            mime="text/csv",
                        )
                    if not skipped.empty:
                        st.subheader("Skipped symbols and reasons")
                        st.dataframe(skipped, use_container_width=True)
                        st.download_button(
                            "Download skipped-symbol diagnostics (CSV)",
                            data=skipped.to_csv(index=False).encode("utf-8"),
                            file_name="multi_stock_skipped_symbols.csv",
                            mime="text/csv",
                        )
                    st.download_button(
                        "Download multi-stock report (CSV)",
                        data=report.to_csv(index=False).encode("utf-8"),
                        file_name="multi_stock_walk_forward_report.csv",
                        mime="text/csv",
                    )
        except (KeyError, TypeError, ValueError) as exc:
            st.error(f"Multi-stock validation could not run: {exc}")
