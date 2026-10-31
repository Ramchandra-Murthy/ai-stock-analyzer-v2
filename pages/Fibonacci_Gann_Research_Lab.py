"""Streamlit interface for the research-only Fibonacci-Gann backtest tools."""

from __future__ import annotations

from io import BytesIO
from math import isfinite

import pandas as pd
import streamlit as st

from components.disclaimer import show_disclaimer
from modules.fibonacci_gann.backtest import BacktestConfig, Candle, run_backtest
from modules.fibonacci_gann.benchmark import compare_with_buy_and_hold
from modules.fibonacci_gann.parameter_sensitivity import evaluate_parameter_sensitivity
from modules.fibonacci_gann.regime_robustness import evaluate_regime_robustness
from modules.fibonacci_gann.walk_forward import evaluate_walk_forward

st.set_page_config(page_title="Fibonacci-Gann Research Lab", page_icon="📐", layout="wide")
st.title("📐 Fibonacci-Gann Research Lab")
show_disclaimer()
st.caption(
    "Research-only historical analysis using your uploaded OHLC and signal data. "
    "No live market-data requests or broker orders are made by this page."
)
st.warning(
    "Backtest results are hypothetical and can be misleading. Check data quality, "
    "signal timing, transaction costs, slippage, and out-of-sample performance before "
    "drawing conclusions. This is not a trade recommendation."
)

with st.expander("CSV format and signal timing", expanded=True):
    st.markdown(
        "Upload a CSV containing **timestamp, open, high, low, close, signal** columns. "
        "The signal must be true/false or 1/0. A signal is assumed known only after that "
        "bar closes; the backtester enters no earlier than the next bar's open. "
        "Rows must be chronological and prices must be valid positive OHLC values."
    )
    st.caption(
        "Regime labels are supplied by you; this page does not automatically classify "
        "trending, sideways, or volatile markets."
    )

data_source = st.radio(
    "Historical data source",
    ("Download daily history", "Upload CSV"),
    horizontal=True,
    help="Downloads use Yahoo Finance through yfinance and are unofficial. Verify prices independently.",
)

if data_source == "Download daily history":
    from datetime import date, timedelta
    from tempfile import TemporaryDirectory

    from scripts.make_research_csv import download_research_csv

    st.markdown("#### Download historical OHLC")
    st.caption(
        "This downloads daily prices into the Research Lab CSV format. "
        "It does not generate Fibonacci-Gann signals; every downloaded signal starts as false."
    )
    download_left, download_middle, download_right = st.columns(3)
    with download_left:
        symbol = st.text_input("Yahoo Finance symbol", value="RELIANCE.NS").strip()
    with download_middle:
        start_date = st.date_input("Start date", value=date.today() - timedelta(days=365 * 5))
    with download_right:
        end_date = st.date_input("End date (exclusive)", value=date.today())

    if st.button("Download historical CSV", type="primary"):
        if not symbol:
            st.error("Enter a Yahoo Finance symbol, such as RELIANCE.NS or ^NSEI.")
        elif start_date >= end_date:
            st.error("Start date must be earlier than the end date.")
        else:
            try:
                with TemporaryDirectory() as temp_dir:
                    output_path = download_research_csv(
                        symbol=symbol,
                        start=start_date.isoformat(),
                        end=end_date.isoformat(),
                        output=f"{temp_dir}/research.csv",
                    )
                    csv_bytes = output_path.read_bytes()
                st.session_state["fibonacci_gann_download_csv"] = csv_bytes
                st.session_state["fibonacci_gann_download_name"] = (
                    f"{symbol.replace('^', '').replace('.', '_')}_research.csv"
                )
                st.success(
                    f"Downloaded and validated {len(pd.read_csv(BytesIO(csv_bytes))):,} daily rows."
                )
            except Exception as exc:
                st.error(
                    "Historical download failed. Check the symbol, dates, and provider availability. "
                    f"Details: {exc}"
                )

    csv_bytes = st.session_state.get("fibonacci_gann_download_csv")
    csv_name = st.session_state.get("fibonacci_gann_download_name", "historical_research.csv")
    if csv_bytes:
        st.download_button(
            "Save downloaded CSV",
            data=csv_bytes,
            file_name=csv_name,
            mime="text/csv",
        )
        st.info(
            "Before running a backtest, replace the placeholder false signals with signals from "
            "your documented, causal strategy. The downloader does not calculate Fibonacci-Gann signals."
        )
        frame = pd.read_csv(BytesIO(csv_bytes))
    else:
        st.info("Choose a symbol and date range, then select Download historical CSV.")
        st.stop()
else:
    uploaded = st.file_uploader("Upload historical CSV", type=["csv"])
    if uploaded is None:
        st.info("Upload a CSV to begin.")
        st.stop()
    try:
        frame = pd.read_csv(BytesIO(uploaded.getvalue()))
    except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as exc:
        st.error(f"Could not read the CSV: {exc}")
        st.stop()

frame.columns = [str(column).strip().lower() for column in frame.columns]
required = {"timestamp", "open", "high", "low", "close", "signal"}
missing = sorted(required - set(frame.columns))
if missing:
    st.error("Missing required columns: " + ", ".join(missing))
    st.stop()
if len(frame) < 2:
    st.error("The CSV must contain at least two data rows.")
    st.stop()

signal_mode = st.radio(
    "Entry signal method",
    ("Use CSV signal column", "Generate daily Fibonacci-Gann signals"),
    horizontal=True,
    help="Generated signals use a transparent research rule based only on prior daily candles.",
)
lookback = 20
if signal_mode == "Generate daily Fibonacci-Gann signals":
    lookback = st.number_input(
        "Prior candles used for swing range",
        min_value=5,
        max_value=120,
        value=20,
        step=1,
        help="The current candle is excluded from the range used to calculate its signal.",
    )
    st.info(
        "Research rule: use the preceding lookback bars to calculate the 38.2%-61.8% "
        "Fibonacci retracement zone and Gann 5/8 level. A signal occurs when the prior "
        "close is in the retracement zone and the current close crosses above 5/8. "
        "The backtester enters no earlier than the next bar open. This is an unvalidated "
        "hypothesis, not a proven profitable strategy."
    )

numeric_columns = ["open", "high", "low", "close"]
for column in numeric_columns:
    frame[column] = pd.to_numeric(frame[column], errors="coerce")
if signal_mode == "Use CSV signal column":
    signal_text = frame["signal"].astype(str).str.strip().str.lower()
    signal_map = {"true": True, "false": False, "1": True, "0": False}
    if not signal_text.isin(signal_map).all():
        st.error("The signal column must contain only true/false or 1/0 values.")
        st.stop()
    frame["signal"] = signal_text.map(signal_map)
frame["timestamp"] = frame["timestamp"].astype(str).str.strip()

try:
    candles = tuple(
        Candle(
            timestamp=row.timestamp,
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
        )
        for row in frame[["timestamp", "open", "high", "low", "close"]].itertuples(index=False)
    )
except (TypeError, ValueError, AttributeError) as exc:
    st.error(f"Could not build OHLC candles: {exc}")
    st.stop()

if signal_mode == "Generate daily Fibonacci-Gann signals":
    from modules.fibonacci_gann.signals import generate_daily_fibonacci_gann_signals

    try:
        signals = generate_daily_fibonacci_gann_signals(candles, lookback=int(lookback))
    except ValueError as exc:
        st.error(f"Could not generate signals: {exc}")
        st.stop()
    frame["signal"] = signals
else:
    signals = tuple(bool(value) for value in frame["signal"].tolist())
signal_count = sum(signals)
st.caption(
    f"Loaded {len(candles):,} candles. Entry signals: {signal_count:,}; "
    f"non-signals: {len(signals) - signal_count:,}. Verify timestamps, signal generation, and data source."
)
if signal_count == 0:
    st.warning(
        "No entry signals are present in this CSV. A backtest with zero trades is expected; "
        "returns and drawdown do not evaluate a strategy. Downloaded CSVs use placeholder "
        "false signals until you add a documented strategy signal."
    )
else:
    st.info(
        f"{signal_count:,} signal bar(s) detected. Signals are assumed known after each bar closes, "
        "and entries occur no earlier than the next bar's open."
    )
st.dataframe(frame.head(10), use_container_width=True, hide_index=True)

st.subheader("Backtest assumptions")
left, middle, right = st.columns(3)
with left:
    capital = st.number_input("Starting capital (₹)", min_value=1000.0, value=10000.0, step=1000.0)
    max_loss = st.number_input(
        "Maximum loss budget per trade (₹)", min_value=1.0, value=500.0, step=50.0
    )
with middle:
    stop_distance = st.number_input(
        "Stop distance (price units)", min_value=0.01, value=2.0, step=0.5
    )
    reward_risk = st.number_input("Reward/risk ratio", min_value=0.1, value=2.0, step=0.1)
with right:
    round_trip_cost = st.number_input(
        "Round-trip cost per unit (₹)", min_value=0.0, value=0.6, step=0.1
    )
    slippage = st.number_input("Slippage per unit per side (₹)", min_value=0.0, value=0.1, step=0.1)

base_config = BacktestConfig(
    capital=capital,
    max_loss_per_trade=max_loss,
    stop_distance=stop_distance,
    reward_risk_ratio=reward_risk,
    round_trip_cost_per_unit=round_trip_cost,
    slippage_per_unit_per_side=slippage,
)

if round_trip_cost == 0 or slippage == 0:
    st.warning(
        "At least one cost assumption is zero. Confirm that this reflects your intended "
        "scenario; zero costs can materially overstate backtest performance."
    )
st.caption(
    "The defaults (₹0.60 round-trip cost and ₹0.10 slippage per unit per side) are "
    "illustrative placeholders, not a broker-specific fee quote. Replace them with your "
    "contract-note costs and realistic fill assumptions."
)
st.caption(
    "Risk note: the ₹ maximum-loss setting is a planned stop-risk budget, not a guaranteed cap. "
    "Gaps through stops can cause larger losses. Reported maximum drawdown uses closed-trade equity "
    "and does not measure intratrade drawdown."
)

st.subheader("Out-of-sample validation settings")
if len(candles) >= 3:
    default_train_size = min(max(int(len(candles) * 0.6), int(lookback) + 1), len(candles) - 2)
    validation_left, validation_right = st.columns(2)
    with validation_left:
        initial_train_size = st.number_input(
            "Initial history candles (not scored)",
            min_value=1,
            max_value=len(candles) - 2,
            value=default_train_size,
            step=1,
            help="The earliest candles are used as prior history; test results start after this point.",
        )
    with validation_right:
        max_test_size = max(2, len(candles) - int(initial_train_size))
        test_size = st.number_input(
            "Candles per test window",
            min_value=2,
            max_value=max_test_size,
            value=min(60, max_test_size),
            step=1,
            help="Windows are evaluated chronologically and do not overlap.",
        )
    st.caption(
        "Walk-forward results are separate, non-compounded test windows. Do not tune parameters "
        "by looking at test results. At least two candles must remain in each scored window."
    )
else:
    initial_train_size = 1
    test_size = 2
    st.info(
        "At least three candles are required for out-of-sample validation; "
        "the ordinary backtest remains available."
    )

if st.button("Run research analysis", type="primary"):
    try:
        baseline = run_backtest(candles, signals, base_config)
        if signal_mode == "Generate daily Fibonacci-Gann signals":
            # Build the fixed research grid here instead of importing the optional
            # helper. This keeps the page compatible with deployments where the
            # parameter_sensitivity module predates build_parameter_grid.
            from modules.fibonacci_gann.signals import generate_daily_fibonacci_gann_signals
            from modules.fibonacci_gann.trend_filter import apply_sma_trend_filter

            sma200_signals = apply_sma_trend_filter(candles, signals, period=200)
            sma200_result = run_backtest(candles, sma200_signals, base_config)
            sensitivity = []
            for grid_lookback in (10, 20, 30, 50):
                for grid_reward_risk in (2.0, 2.5, 3.0):
                    case_config = BacktestConfig(
                        capital=base_config.capital,
                        max_loss_per_trade=base_config.max_loss_per_trade,
                        stop_distance=base_config.stop_distance,
                        reward_risk_ratio=grid_reward_risk,
                        round_trip_cost_per_unit=base_config.round_trip_cost_per_unit,
                        slippage_per_unit_per_side=base_config.slippage_per_unit_per_side,
                    )
                    case_signals = generate_daily_fibonacci_gann_signals(
                        candles, lookback=grid_lookback
                    )
                    item = evaluate_parameter_sensitivity(
                        candles,
                        case_signals,
                        {f"Lookback {grid_lookback} / R:R {grid_reward_risk:g}": case_config},
                    )[0]
                    sensitivity.append((grid_lookback, item))
        else:
            variants = {
                "CSV signals / baseline": base_config,
                "CSV signals / R:R 2.5": BacktestConfig(
                    capital=capital,
                    max_loss_per_trade=max_loss,
                    stop_distance=stop_distance,
                    reward_risk_ratio=2.5,
                    round_trip_cost_per_unit=round_trip_cost,
                    slippage_per_unit_per_side=slippage,
                ),
                "CSV signals / R:R 3.0": BacktestConfig(
                    capital=capital,
                    max_loss_per_trade=max_loss,
                    stop_distance=stop_distance,
                    reward_risk_ratio=3.0,
                    round_trip_cost_per_unit=round_trip_cost,
                    slippage_per_unit_per_side=slippage,
                ),
            }
            sensitivity = [
                (int(lookback), item)
                for item in evaluate_parameter_sensitivity(candles, signals, variants)
            ]
    except (ValueError, TypeError, OverflowError) as exc:
        st.error(f"Analysis could not be completed: {exc}")
        st.stop()

    if signal_mode == "Generate daily Fibonacci-Gann signals":
        st.subheader("200-day SMA trend-filter comparison")
        st.caption(
            "Research-only comparison using the same OHLC data, costs, position sizing, and "
            "backtest settings. The filtered variant retains a signal only when that bar closes "
            "above its trailing 200-day simple moving average; signals before 200 closes are "
            "suppressed. Entry remains no earlier than the following bar open. This full-period "
            "comparison is exploratory/in-sample, not evidence of profitability."
        )
        trend_rows = []
        for label, result in (("Baseline", baseline), ("Close above SMA 200", sma200_result)):
            trend_rows.append(
                {
                    "Variant": label,
                    "Trades": len(result.trades),
                    "Ending capital (₹)": round(result.ending_capital, 2),
                    "Return (%)": round(result.total_return_pct, 2),
                    "Realized max drawdown (%)": round(result.max_drawdown_pct, 2),
                    "Max intratrade drawdown (%)": round(result.max_intratrade_drawdown_pct, 2),
                    "Win rate (%)": round(result.win_rate_pct, 2),
                    "Expectancy/trade (₹)": round(result.expectancy_per_trade, 2),
                    "Profit factor": (
                        round(result.profit_factor, 3) if isfinite(result.profit_factor) else "∞"
                    ),
                }
            )
        st.dataframe(pd.DataFrame(trend_rows), use_container_width=True, hide_index=True)

    st.subheader("Baseline result")
    if signal_count > 0 and not baseline.trades:
        st.warning(
            "Signals were present, but the backtester generated no trades. Check signal timing, "
            "available following candles, and the backtest's entry/position rules before interpreting metrics."
        )
    elif signal_count == 0:
        st.info(
            "This is a no-signal diagnostic, not a strategy performance result. "
            "Add valid strategy signals before assessing profitability or risk."
        )
    metrics = st.columns(5)
    metrics[0].metric("Ending capital", f"₹{baseline.ending_capital:,.2f}")
    metrics[1].metric("Total return", f"{baseline.total_return_pct:.2f}%")
    metrics[2].metric("Realized max drawdown", f"{baseline.max_drawdown_pct:.2f}%")
    metrics[3].metric("Win rate", f"{baseline.win_rate_pct:.2f}%")
    st.metric(
        "Max intratrade drawdown (conservative OHLC estimate)",
        f"{baseline.max_intratrade_drawdown_pct:.2f}%",
    )
    metrics[4].metric("Trades", len(baseline.trades))

    if baseline.total_return_pct <= 0:
        st.error(
            "The baseline did not make money under the selected assumptions. "
            "Do not use this configuration for live trading; investigate signal quality "
            "and unseen-period performance instead of tuning to this same history."
        )
    if len(baseline.trades) < 30:
        st.warning(
            f"Only {len(baseline.trades)} baseline trades were generated. Treat the metrics "
            "as preliminary; small samples can produce unstable win rates and drawdowns."
        )

    st.subheader("Transaction-cost stress test")
    stress_config = BacktestConfig(
        capital=base_config.capital,
        max_loss_per_trade=base_config.max_loss_per_trade,
        stop_distance=base_config.stop_distance,
        reward_risk_ratio=base_config.reward_risk_ratio,
        round_trip_cost_per_unit=max(
            base_config.round_trip_cost_per_unit * 1.5, base_config.round_trip_cost_per_unit + 0.3
        ),
        slippage_per_unit_per_side=max(
            base_config.slippage_per_unit_per_side * 2, base_config.slippage_per_unit_per_side + 0.1
        ),
    )
    stress_result = run_backtest(candles, signals, stress_config)
    stress_rows = [
        {
            "Scenario": "Configured costs",
            "Round-trip cost/unit (₹)": base_config.round_trip_cost_per_unit,
            "Slippage/side/unit (₹)": base_config.slippage_per_unit_per_side,
            "Trades": len(baseline.trades),
            "Return (%)": round(baseline.total_return_pct, 2),
            "Ending capital (₹)": round(baseline.ending_capital, 2),
        },
        {
            "Scenario": "Higher-cost stress",
            "Round-trip cost/unit (₹)": stress_config.round_trip_cost_per_unit,
            "Slippage/side/unit (₹)": stress_config.slippage_per_unit_per_side,
            "Trades": len(stress_result.trades),
            "Return (%)": round(stress_result.total_return_pct, 2),
            "Ending capital (₹)": round(stress_result.ending_capital, 2),
        },
    ]
    st.dataframe(pd.DataFrame(stress_rows), use_container_width=True, hide_index=True)
    st.caption(
        "The stress case raises both cost assumptions mechanically; it is a sensitivity "
        "check, not a claim about actual brokerage charges. Position sizing is recalculated "
        "under each cost scenario."
    )
    if stress_result.total_return_pct < baseline.total_return_pct:
        st.warning(
            "Performance deteriorates under higher costs. A strategy that depends on optimistic "
            "fills or low fees is not robust enough for live use."
        )

    st.subheader("Parameter sensitivity")
    if signal_mode == "Generate daily Fibonacci-Gann signals":
        st.caption(
            "12 full-period combinations are shown for exploratory sensitivity only. "
            "Each lookback regenerates its own causal signals. These are not out-of-sample "
            "scores; do not select parameters from this table. Use the walk-forward results below."
        )
    else:
        st.caption(
            "CSV signals are fixed and cannot be regenerated for different lookbacks. "
            "This table varies reward/risk only; the selected lookback does not apply to CSV signals."
        )
    sensitivity_rows = [
        {
            "Lookback": (
                lookback_value
                if signal_mode == "Generate daily Fibonacci-Gann signals"
                else "CSV signals"
            ),
            "Variant": item.variant,
            "Stop distance": item.config.stop_distance,
            "Reward/risk": item.config.reward_risk_ratio,
            "Trades": len(item.result.trades),
            "Ending capital (₹)": round(item.result.ending_capital, 2),
            "Return (%)": round(item.result.total_return_pct, 2),
            "Realized max drawdown (%)": round(item.result.max_drawdown_pct, 2),
            "Max intratrade drawdown (%)": round(item.result.max_intratrade_drawdown_pct, 2),
            "Win rate (%)": round(item.result.win_rate_pct, 2),
            "Expectancy/trade (₹)": round(item.result.expectancy_per_trade, 2),
            "Profit factor": (
                round(item.result.profit_factor, 3) if isfinite(item.result.profit_factor) else "∞"
            ),
        }
        for lookback_value, item in sensitivity
    ]
    st.dataframe(pd.DataFrame(sensitivity_rows), use_container_width=True, hide_index=True)

    st.subheader("Out-of-sample walk-forward validation")
    if signal_mode == "Generate daily Fibonacci-Gann signals":
        from modules.fibonacci_gann.signals import generate_daily_fibonacci_gann_signals
        from modules.fibonacci_gann.trend_filter import apply_sma_trend_filter

        def _latest_causal_signal(history, _config):
            # The rule only needs the latest bar plus its preceding lookback bars.
            window = tuple(history[-(int(lookback) + 1) :])
            if len(window) <= int(lookback):
                return False
            return generate_daily_fibonacci_gann_signals(window, lookback=int(lookback))[-1]

        def _latest_causal_sma200_signal(history, _config):
            # Build signals only from the available prefix; the SMA includes only
            # closes known at the current signal bar's close.
            history_signals = generate_daily_fibonacci_gann_signals(history, lookback=int(lookback))
            return apply_sma_trend_filter(history, history_signals, period=200)[-1]

        try:
            folds = evaluate_walk_forward(
                candles,
                _latest_causal_signal,
                base_config,
                initial_train_size=int(initial_train_size),
                test_size=int(test_size),
            )
            sma200_folds = evaluate_walk_forward(
                candles,
                _latest_causal_sma200_signal,
                base_config,
                initial_train_size=int(initial_train_size),
                test_size=int(test_size),
            )
            fold_rows = []
            for fold, sma_fold in zip(folds, sma200_folds, strict=True):
                fold_candles = tuple(
                    candle
                    for candle in candles
                    if fold.test_start <= candle.timestamp <= fold.test_end
                )
                comparison = compare_with_buy_and_hold(fold_candles, fold.result)
                fold_rows.append(
                    {
                        "Training ends": fold.train_end,
                        "Test starts": fold.test_start,
                        "Test ends": fold.test_end,
                        "Test candles": fold.test_candle_count,
                        "Baseline trades": len(fold.result.trades),
                        "Baseline return (%)": round(fold.result.total_return_pct, 2),
                        "Baseline drawdown (%)": round(fold.result.max_drawdown_pct, 2),
                        "SMA200 trades": len(sma_fold.result.trades),
                        "SMA200 return (%)": round(sma_fold.result.total_return_pct, 2),
                        "SMA200 drawdown (%)": round(sma_fold.result.max_drawdown_pct, 2),
                        "Buy-and-hold return (%)": round(comparison.benchmark_return_pct, 2),
                    }
                )
            st.dataframe(pd.DataFrame(fold_rows), use_container_width=True, hide_index=True)
            baseline_oos_pnl = sum(
                fold.result.ending_capital - base_config.capital for fold in folds
            )
            sma200_oos_pnl = sum(
                fold.result.ending_capital - base_config.capital for fold in sma200_folds
            )
            oos_summary_rows = []
            for label, variant_folds, total_pnl in (
                ("Baseline", folds, baseline_oos_pnl),
                ("Close above SMA 200", sma200_folds, sma200_oos_pnl),
            ):
                oos_summary_rows.append(
                    {
                        "Variant": label,
                        "Test windows": len(variant_folds),
                        "Total OOS trades": sum(len(fold.result.trades) for fold in variant_folds),
                        "Positive-return windows": sum(
                            fold.result.total_return_pct > 0 for fold in variant_folds
                        ),
                        "Mean window return (%)": round(
                            sum(fold.result.total_return_pct for fold in variant_folds)
                            / len(variant_folds),
                            2,
                        ),
                        "Sum of window P&L (₹)": round(total_pnl, 2),
                    }
                )
            st.markdown("**Out-of-sample summary (separate, non-compounded folds)**")
            st.dataframe(pd.DataFrame(oos_summary_rows), use_container_width=True, hide_index=True)
            st.caption(
                "Window P&L is summed across independent folds, each starting with the configured "
                "capital; it is not a compounded account curve. Mean window return gives each fold "
                "equal weight, including the shorter final fold."
            )
            st.caption(
                "Baseline and SMA200-filtered signals are evaluated on identical chronological, "
                "non-overlapping test windows with the same configured costs and position sizing. "
                "Each fold starts with configured capital; returns are not compounded. The SMA200 "
                "filter suppresses signals until 200 closes are available. Buy-and-hold uses "
                "close-to-close prices and excludes dividends, fees, taxes, and slippage. This is "
                "an exploratory comparison, not proof of profitability."
            )
            baseline_trade_count = sum(row["Baseline trades"] for row in fold_rows)
            sma200_trade_count = sum(row["SMA200 trades"] for row in fold_rows)
            if baseline_trade_count == 0 and sma200_trade_count == 0:
                st.warning(
                    "No trades occurred in any out-of-sample window. "
                    "This does not validate the strategy."
                )
            elif baseline_trade_count < 10 or sma200_trade_count < 10:
                st.warning(
                    "At least one variant generated fewer than 10 out-of-sample trades; "
                    "results are too sparse for strong conclusions."
                )
        except (ValueError, TypeError, OverflowError) as exc:
            st.error(f"Out-of-sample validation could not be completed: {exc}")
    else:
        st.info(
            "Walk-forward signal regeneration is available when "
            "'Generate daily Fibonacci-Gann signals' "
            "is selected. CSV-supplied signals are not assumed to be reproducible from OHLC history."
        )

    st.subheader("Full-period buy-and-hold benchmark")
    try:
        full_period_comparison = compare_with_buy_and_hold(candles, baseline)
        benchmark_columns = st.columns(4)
        benchmark_columns[0].metric(
            "Strategy return", f"{full_period_comparison.strategy_return_pct:.2f}%"
        )
        benchmark_columns[1].metric(
            "Buy-and-hold return", f"{full_period_comparison.benchmark_return_pct:.2f}%"
        )
        benchmark_columns[2].metric(
            "Excess return", f"{full_period_comparison.excess_return_pct:.2f} pp"
        )
        benchmark_columns[3].metric(
            "Benchmark max drawdown", f"{full_period_comparison.benchmark_max_drawdown_pct:.2f}%"
        )
        if full_period_comparison.insufficient_trades:
            st.warning(
                f"Only {full_period_comparison.trade_count} trades were generated; "
                "the minimum sample-size flag is active."
            )
        st.caption(
            "Full-period comparison is descriptive and may be in-sample. "
            "Buy-and-hold excludes dividends, fees, taxes, and slippage. Use the separate walk-forward "
            "results for a more cautious view of unseen periods."
        )
    except (ValueError, TypeError, OverflowError) as exc:
        st.error(f"Benchmark comparison could not be completed: {exc}")

    st.subheader("Optional caller-labelled regime windows")
    st.markdown(
        "Enter one non-overlapping window per line as **label,start_index,end_index**. "
        "Indices are zero-based and the end index is exclusive. Labels are your own "
        "classification, not inferred by the app."
    )
    regime_text = st.text_area(
        "Regime windows",
        placeholder="trending,0,100\nsideways,100,200",
        help="Each window must include at least two candles and fit within the uploaded data.",
    )
    if regime_text.strip():
        try:
            regimes: dict[str, tuple[int, int]] = {}
            for line_number, line in enumerate(regime_text.splitlines(), start=1):
                parts = [part.strip() for part in line.split(",")]
                if len(parts) != 3:
                    raise ValueError(f"Line {line_number}: use label,start_index,end_index")
                label, start_text, end_text = parts
                if label in regimes:
                    raise ValueError(f"Line {line_number}: duplicate label {label!r}")
                regimes[label] = (int(start_text), int(end_text))
            regime_results = evaluate_regime_robustness(
                candles, signals, base_config, regimes=regimes
            )
            regime_rows = [
                {
                    "Label": item.regime,
                    "Start index": item.start_index,
                    "End index (exclusive)": item.end_index,
                    "Candles": item.candle_count,
                    "Trades": len(item.result.trades),
                    "Return (%)": round(item.result.total_return_pct, 2),
                    "Realized max drawdown (%)": round(item.result.max_drawdown_pct, 2),
                    "Max intratrade drawdown (%)": round(
                        item.result.max_intratrade_drawdown_pct, 2
                    ),
                    "Win rate (%)": round(item.result.win_rate_pct, 2),
                }
                for item in regime_results
            ]
            st.dataframe(pd.DataFrame(regime_rows), use_container_width=True, hide_index=True)
        except (ValueError, TypeError) as exc:
            st.error(f"Regime analysis could not be completed: {exc}")

    trades = pd.DataFrame([trade.__dict__ for trade in baseline.trades])
    st.subheader("Baseline trade ledger")
    if trades.empty:
        st.info("No trades were generated for these signals and assumptions.")
    else:
        st.dataframe(trades, use_container_width=True, hide_index=True)
        st.download_button(
            "Download trade ledger CSV",
            data=trades.to_csv(index=False).encode("utf-8"),
            file_name="fibonacci_gann_research_trades.csv",
            mime="text/csv",
        )
