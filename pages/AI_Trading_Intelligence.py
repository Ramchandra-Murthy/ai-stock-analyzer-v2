"""Streamlit page for the separate AI trading intelligence module."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.ai_scanner import scan_universe
from ai_trading.decision_engine import build_signal_decision
from ai_trading.features import build_features
from ai_trading.ml_model import predict_latest, train_model
from ai_trading.ml_scanner import scan_universe as scan_ml_universe
from ai_trading.signal_history import attach_outcomes, record_signal
from ai_trading.walk_forward import walk_forward_backtest
from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES
from services.resilient_market_data import download_symbol_frames

st.set_page_config(page_title="AI Trading Intelligence", page_icon="🧠", layout="wide")

st.title("🧠 AI Trading Intelligence")
st.caption("AI-oriented market feature and signal research. No broker orders are submitted.")

left, right = st.columns(2)
with left:
    exchange = st.selectbox("Exchange", ["NSE", "BSE"])
    universe = NSE_CANDIDATES if exchange == "NSE" else BSE_CANDIDATES
    count = st.slider("Symbols to scan", 10, min(50, len(universe)), 20, 5)
with right:
    period = st.selectbox("Training / analysis history", ["6mo", "1y", "2y"], index=1)

if st.button("Run AI Trading Scan", type="primary"):
    with st.spinner(f"Analyzing {count} {exchange} symbols..."):
        result = scan_universe(universe[:count], exchange=exchange, period=period)

    diagnostics = result.attrs.get("scan_diagnostics", {})
    if result.empty:
        missing = diagnostics.get("missing", [])
        detail = f" Missing/unresolved: {len(missing)} symbols." if missing else ""
        st.error("AI scan returned no usable market data after bounded retries." + detail)
        st.caption(
            "No signal was generated from missing or synthetic data; " "retry during market hours."
        )
        st.stop()

    usable = diagnostics.get("usable", len(result))
    requested = diagnostics.get("requested", count)
    if usable < requested:
        st.warning(
            f"Partial market-data coverage: {usable}/{requested} symbols. "
            "Results are research-only until coverage is complete."
        )
    else:
        st.success(f"Analyzed {len(result)} symbols with complete market-data coverage.")
    st.subheader("AI Trading Opportunities")
    st.dataframe(result.head(10), use_container_width=True, hide_index=True)

    st.subheader("Signal distribution")
    st.bar_chart(result["signal"].value_counts())

    st.subheader("AI confidence")
    st.bar_chart(result.set_index("symbol")["confidence_pct"].head(10))

    st.info(
        "The scanner above is the deterministic baseline. The ML validation panel below "
        "trains a separate leakage-safe model using a chronological holdout; it does not "
        "place broker orders."
    )

st.divider()
st.subheader("🔎 Multi-Stock ML Scanner")
st.caption(
    "Trains a separate leakage-safe model for each selected symbol and combines ML probability, "
    "validation quality, trend and market-regime context into the final AI decision. "
    "When enough completed signal history exists, learned outcome data also adjusts confidence "
    "within a bounded range without changing the signal direction."
)

scan_left, scan_mid, scan_right = st.columns(3)
with scan_left:
    ml_count = st.slider(
        "ML symbols",
        5,
        min(30, len(universe)),
        min(10, len(universe)),
        5,
        key="ml_scan_count",
    )
with scan_mid:
    scan_horizon = st.slider(
        "ML horizon (days)",
        1,
        20,
        5,
        key="ml_scan_horizon",
    )
with scan_right:
    scan_threshold = st.slider(
        "ML threshold (%)",
        0.0,
        5.0,
        1.0,
        0.5,
        key="ml_scan_threshold",
    )

if st.button("Run Multi-Stock ML Scan", type="primary"):
    with st.spinner(f"Training {ml_count} {exchange} models..."):
        adaptive_history = st.session_state.get("ai_signal_history")
        if not isinstance(adaptive_history, pd.DataFrame):
            adaptive_history = None
        try:
            ml_result = scan_ml_universe(
                universe[:ml_count],
                exchange=exchange,
                period="5y",
                horizon=scan_horizon,
                threshold=scan_threshold / 100.0,
                adaptive_history=adaptive_history,
            )
        except (TypeError, ValueError, KeyError) as exc:
            st.error(f"Multi-Stock ML Scanner failed: {exc}")
            ml_result = pd.DataFrame()
    st.session_state["ai_ml_result"] = ml_result
    st.session_state["ai_ml_exchange"] = exchange
    st.session_state["ai_ml_horizon"] = scan_horizon

ml_result = st.session_state.get("ai_ml_result")
if isinstance(ml_result, pd.DataFrame):
    if ml_result.empty:
        st.warning("No symbols produced a valid ML result.")
    else:
        st.success(f"Validated {len(ml_result)} stock models.")

        signal_filter = st.multiselect(
            "Signals to display",
            ["LONG", "SHORT", "NEUTRAL"],
            default=["LONG", "SHORT", "NEUTRAL"],
            key="ml_signal_filter",
        )
        regime_filter = st.multiselect(
            "Market regimes to display",
            ["BULLISH", "BEARISH", "RANGE / MIXED", "INSUFFICIENT DATA"],
            default=["BULLISH", "BEARISH", "RANGE / MIXED", "INSUFFICIENT DATA"],
            key="ml_regime_filter",
        )
        min_confidence = st.slider(
            "Minimum AI confidence (%)",
            0.0,
            100.0,
            0.0,
            5.0,
            key="ml_min_confidence",
        )

        filtered = ml_result[
            ml_result["signal"].isin(signal_filter)
            & ml_result["regime"].isin(regime_filter)
            & (ml_result["confidence_pct"] >= min_confidence)
        ].copy()

        metric1, metric2, metric3, metric4 = st.columns(4)
        metric1.metric("Models validated", len(ml_result))
        metric2.metric("Displayed", len(filtered))
        metric3.metric(
            "Average confidence",
            f"{filtered['confidence_pct'].mean():.1f}%" if not filtered.empty else "N/A",
        )
        metric4.metric(
            "Average adaptive adjustment",
            f"{filtered['adaptive_adjustment_pct'].mean():+.1f}%" if not filtered.empty else "N/A",
        )

        display_columns = [
            "symbol",
            "latest_price",
            "signal",
            "confidence_pct",
            "raw_confidence_pct",
            "adaptive_adjustment_pct",
            "adaptive_samples",
            "probability_up_pct",
            "validation_pct",
            "trend_pct",
            "regime",
            "regime_strength_pct",
            "decision_reason",
        ]
        st.dataframe(
            filtered[display_columns].head(20),
            use_container_width=True,
            hide_index=True,
        )

        chart_left, chart_right = st.columns(2)
        with chart_left:
            st.subheader("AI signal distribution")
            st.bar_chart(filtered["signal"].value_counts())
        with chart_right:
            st.subheader("Market-regime distribution")
            st.bar_chart(filtered["regime"].value_counts())

        st.subheader("AI confidence by symbol")
        if not filtered.empty:
            st.bar_chart(
                filtered.set_index("symbol")[["raw_confidence_pct", "confidence_pct"]].head(20)
            )

        st.download_button(
            "Download adaptive AI scan CSV",
            filtered.to_csv(index=False).encode("utf-8"),
            "ai_adaptive_ai_scan.csv",
            "text/csv",
            key="download_ai_regime_scan",
        )

        st.caption(
            "Ranking is based on the regime-aware decision engine's confidence and the "
            "scanner's historical validation metrics. These measurements are not guarantees "
            "of future returns."
        )

        if st.button("Record Current ML Signals", key="record_ml_signals"):
            records = st.session_state.setdefault("ai_signal_records", [])
            for row in filtered.to_dict("records"):
                records.append(
                    record_signal(
                        symbol=str(row["symbol"]),
                        exchange=exchange,
                        signal=str(row["signal"]),
                        probability_up=float(row["probability_up_pct"]) / 100.0,
                        confidence_pct=float(row["confidence_pct"]),
                        raw_confidence_pct=float(row["raw_confidence_pct"]),
                        adaptive_confidence_pct=float(row["confidence_pct"]),
                        adaptive_adjustment_pct=float(row["adaptive_adjustment_pct"]),
                        adaptive_samples=int(row["adaptive_samples"]),
                        validation_pct=float(row["validation_pct"]),
                        trend_pct=float(row["trend_pct"]),
                        entry_price=float(row["latest_price"]),
                        horizon_days=int(st.session_state.get("ai_ml_horizon", scan_horizon)),
                    )
                )
            st.session_state["ai_signal_history"] = attach_outcomes(records, {})
            st.success(f"Recorded {len(filtered)} displayed AI signals.")

st.divider()
st.subheader("🧩 Unified AI Signal Explainability")
st.caption(
    "Breaks the unified ML decision into model probability, validation quality, "
    "trend contribution, "
    "confidence and the final signal reason. Historical model measurements only."
)

explain_left, explain_right = st.columns(2)
with explain_left:
    explain_symbol = st.selectbox(
        "Explain signal for",
        universe[: min(30, len(universe))],
        key="explain_symbol",
    )
with explain_right:
    explain_horizon = st.slider(
        "Explainability horizon (days)",
        1,
        20,
        5,
        key="explain_horizon",
    )

if st.button("Generate AI Signal Explanation", type="secondary"):
    ticker = (
        f"{str(explain_symbol).strip().upper()}.NS"
        if exchange == "NSE"
        else f"{str(explain_symbol).strip().upper()}.BO"
    )
    with st.spinner(f"Explaining {ticker}..."):
        explain_frames, _explain_diagnostics = download_symbol_frames(
            [ticker],
            period="5y",
            interval="1d",
            auto_adjust=False,
            batch_size=1,
            timeout=15,
        )
        explain_history = explain_frames.get(ticker, pd.DataFrame())
        if explain_history.empty:
            st.error(
                "AI signal explanation could not obtain market data after bounded retries. "
                "No fallback or synthetic prices are used."
            )
            st.stop()

    try:
        explain_model, explain_validation = train_model(
            explain_history,
            horizon=explain_horizon,
            threshold=0.01,
        )
        explain_prediction = predict_latest(explain_model, explain_history)
    except (TypeError, ValueError, KeyError) as exc:
        st.error(f"AI signal explanation could not run: {exc}")
    else:
        explain_features = build_features(explain_history).iloc[-1]
        return_score = max(-1.0, min(1.0, float(explain_features["return_5"]) * 4.0))
        ema_score = max(-1.0, min(1.0, float(explain_features["ema_gap"]) * 5.0))
        trend_score = (return_score + ema_score) / 2.0
        decision = build_signal_decision(
            probability_up=float(explain_prediction["probability_up"]),
            accuracy=explain_validation.accuracy,
            roc_auc=explain_validation.roc_auc,
            trend_score=trend_score,
        )

        metric1, metric2, metric3, metric4 = st.columns(4)
        metric1.metric("Final signal", decision.signal)
        metric2.metric("Unified confidence", f"{decision.confidence_pct:.1f}%")
        metric3.metric("Model confidence", f"{decision.model_confidence_pct:.1f}%")
        metric4.metric("Validation quality", f"{decision.validation_pct:.1f}%")

        detail = pd.DataFrame(
            {
                "Component": ["ML probability", "Validation", "Trend", "Unified confidence"],
                "Value": [
                    f"{float(explain_prediction['probability_up']):.1%}",
                    f"{decision.validation_pct:.1f}%",
                    f"{decision.trend_pct:.1f}%",
                    f"{decision.confidence_pct:.1f}%",
                ],
            }
        )
        st.dataframe(detail, use_container_width=True, hide_index=True)
        st.info(f"Decision reason: {decision.reason}")
        st.caption(
            "The explanation reuses the same unified decision engine as the multi-stock scanner. "
            "It is a research/paper-trading signal and does not place broker orders."
        )

st.divider()
st.subheader("🤖 ML Model Validation")
st.caption(
    "Train and validate a directional classifier on one symbol before using ML signals "
    "in a broader scanner."
)

ml_left, ml_mid, ml_right = st.columns(3)
with ml_left:
    ml_symbol = st.selectbox("Training symbol", universe[: min(30, len(universe))])
with ml_mid:
    horizon = st.slider("Forward horizon (days)", 1, 20, 5)
with ml_right:
    threshold_pct = st.slider("Positive-return threshold", 0.0, 5.0, 1.0, 0.5)

if st.button("Train & Validate ML Model", type="secondary"):
    ticker = (
        f"{str(ml_symbol).strip().upper()}.NS"
        if exchange == "NSE"
        else f"{str(ml_symbol).strip().upper()}.BO"
    )
    with st.spinner(f"Training on {ticker}..."):
        history_frames, _history_diagnostics = download_symbol_frames(
            [ticker],
            period="5y",
            interval="1d",
            auto_adjust=False,
            batch_size=1,
            timeout=15,
        )
        history = history_frames.get(ticker, pd.DataFrame())
        if history.empty:
            st.error(
                "ML training could not obtain market data after bounded retries. "
                "No fallback or synthetic prices are used."
            )
            st.stop()

    try:
        model, validation = train_model(
            history,
            horizon=horizon,
            threshold=threshold_pct / 100.0,
        )
        prediction = predict_latest(model, history)
    except (TypeError, ValueError, KeyError) as exc:
        st.error(f"ML validation could not run: {exc}")
    else:
        metric1, metric2, metric3, metric4 = st.columns(4)
        metric1.metric("Accuracy", f"{validation.accuracy:.1%}")
        metric2.metric(
            "ROC-AUC",
            f"{validation.roc_auc:.3f}" if validation.roc_auc is not None else "N/A",
        )
        metric3.metric("Train samples", validation.train_samples)
        metric4.metric("Test samples", validation.test_samples)

        st.write(
            f"Latest ML signal: **{prediction['signal']}** · "
            f"Probability up: **{float(prediction['probability_up']):.1%}** · "
            f"Model confidence: **{float(prediction['confidence']):.1%}**"
        )
        st.caption(
            "Validation uses earlier observations for training and later observations "
            "for testing. Metrics are historical validation measurements, not guarantees "
            "of future trading performance."
        )

st.divider()
st.subheader("📈 AI Walk-Forward Backtest")
st.caption(
    "Replays the ML strategy chronologically with an expanding training window. "
    "Each test trade uses only information available before entry and holds for the "
    "selected horizon."
)

bt_left, bt_mid, bt_right = st.columns(3)
with bt_left:
    bt_initial_train = st.slider(
        "Initial training bars",
        60,
        300,
        100,
        20,
        key="bt_initial_train",
    )
    bt_long_probability = st.slider(
        "LONG probability",
        0.50,
        0.90,
        0.55,
        0.01,
        key="bt_long_probability",
    )
with bt_mid:
    bt_horizon = st.slider(
        "Backtest horizon (days)",
        1,
        20,
        5,
        key="bt_horizon",
    )
    bt_short_probability = st.slider(
        "SHORT probability",
        0.10,
        0.50,
        0.45,
        0.01,
        key="bt_short_probability",
    )
with bt_right:
    bt_threshold = st.slider(
        "Training threshold (%)",
        0.0,
        5.0,
        1.0,
        0.5,
        key="bt_threshold",
    )
    bt_cost = st.slider(
        "Transaction cost (bps/side)",
        0.0,
        50.0,
        10.0,
        1.0,
        key="bt_cost",
    )

if st.button("Run Walk-Forward Backtest", type="primary"):
    ticker = (
        f"{str(ml_symbol).strip().upper()}.NS"
        if exchange == "NSE"
        else f"{str(ml_symbol).strip().upper()}.BO"
    )
    with st.spinner(f"Backtesting {ticker}..."):
        history_frames, history_diagnostics = download_symbol_frames(
            [ticker],
            period="5y",
            interval="1d",
            auto_adjust=False,
            batch_size=1,
            timeout=15,
        )
        history = history_frames.get(ticker, pd.DataFrame())

    if history.empty:
        st.error(
            "Walk-forward backtest could not obtain historical market data after bounded retries. "
            "No fallback or synthetic prices are used."
        )
        st.stop()

    if not history_diagnostics.get("usable", 0):
        st.warning(
            "Market-data diagnostics did not confirm usable coverage; treat results cautiously."
        )

    try:
        trades, backtest = walk_forward_backtest(
            history,
            horizon=bt_horizon,
            threshold=bt_threshold / 100.0,
            long_probability=bt_long_probability,
            short_probability=bt_short_probability,
            initial_train=bt_initial_train,
            transaction_cost_bps=bt_cost,
        )
    except (TypeError, ValueError, KeyError) as exc:
        st.error(f"Walk-forward backtest could not run: {exc}")
    else:
        metric1, metric2, metric3, metric4, metric5 = st.columns(5)
        metric1.metric("Total return", f"{backtest.total_return:.1%}")
        metric2.metric("Max drawdown", f"{backtest.max_drawdown:.1%}")
        metric3.metric("Trades", backtest.trades)
        metric4.metric("Win rate", f"{backtest.win_rate:.1%}")
        metric5.metric(
            "Profit factor",
            f"{backtest.profit_factor:.2f}" if backtest.profit_factor is not None else "N/A",
        )

        chart = trades.set_index("exit_index")[["equity"]]
        st.line_chart(chart)
        st.dataframe(
            trades[
                [
                    "entry_index",
                    "exit_index",
                    "signal",
                    "probability_up",
                    "entry_price",
                    "exit_price",
                    "gross_return",
                    "transaction_cost",
                    "net_return",
                    "equity",
                    "drawdown",
                ]
            ].tail(25),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "This is a historical simulation, not a live strategy or a guarantee "
            "of future performance. Transaction costs are applied on entry and exit; "
            "slippage, taxes, and liquidity effects are not modeled."
        )
