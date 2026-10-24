"""Streamlit page for objective intraday opportunity screening."""

# ruff: noqa: I001

import pandas as pd
import streamlit as st

from api.main import _SCAN_MANAGER
from scanner.day_trader_opportunity import scan_day_trader_opportunities
from scanner.price_jump_history import append_price_jump_snapshot
from scanner.price_jump_history_analytics import summarize_price_jump_history
from services.price_jump_watchlist_delta import compare_watchlists
from services.intraday_alert_engine import (
    alert_history_frame,
    append_alert_history,
    detect_intraday_alerts,
)
from services.intraday_auto_refresh import (
    ALLOWED_REFRESH_SECONDS,
    DEFAULT_REFRESH_SECONDS,
    market_is_open,
    next_refresh_seconds,
    refresh_label,
)
from services.intraday_dynamic_filter import filter_intraday_candidates
from services.intraday_exchange_summary import exchange_summary
from services.intraday_health import assess_scan_health
from services.intraday_health_history import (
    health_history_frame,
    record_health_observation,
)
from services.intraday_market_regime import classify_scan_regime
from services.intraday_multi_window import multi_window_frame, record_multi_window_outcomes
from services.intraday_position_sizing import calculate_position_size
from services.intraday_quality_dashboard import dashboard_summary
from services.intraday_risk_planning import risk_plan_frame
from services.intraday_scan_delta import snapshot_delta_frame
from services.intraday_scan_snapshot import record_scan_snapshot, snapshot_frame
from services.intraday_session import reset_intraday_session
from services.intraday_setup_evaluation import setup_statistics
from services.intraday_setup_monitor import monitor_frame, record_setup_observations
from services.intraday_setup_outcome import outcomes_frame, record_setup_outcomes
from services.intraday_setup_regime import regime_statistics
from services.intraday_setup_scorecard import scorecard_frame
from services.intraday_signal_validation import (
    build_signal_validation_frame,
    validation_summary,
)
from services.options_analytics import fetch_option_chain, summarize_option_chain
from services.intraday_state_history import (
    record_setup_state_transitions,
    transitions_frame,
)
from services.intraday_trade_analytics import (
    performance_summary,
    setup_performance,
    side_performance,
)
from services.intraday_trade_journal import add_trade, journal_frame, journal_summary
from services.market_status import describe_market_status

# fmt: off

st.set_page_config(
    page_title="Day-Trader Opportunity Scanner",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Day-Trader Opportunity Scanner")
control_left, control_right = st.columns([3, 1])
with control_left:
    st.caption(
        "Session data is local to this Streamlit session and should be refreshed for a new "
        "trading session."
    )
with control_right:
    if st.button("Reset intraday session", type="secondary"):
        reset_intraday_session(st.session_state)
        st.rerun()

st.caption(
    "Ranks observable intraday momentum, volume, range and breakout conditions. "
    "It is a screening tool, not a profit predictor or trade instruction."
)

st.info(
    "The scanner rescans the selected NSE/BSE candidate universe on each run. "
    "Results can change as intraday price, volume and setup conditions change. "
    "Low-priced stocks are shown using a configurable price threshold. "
    "There is no universal formal definition of a penny stock. "
    "The current candidate universe is limited to the symbols maintained by this app."
)

st.subheader("📈 Options Analytics")
st.caption(
    "Options analytics uses NSE index option-chain data first, with Yahoo Finance as a "
    "fallback. It reports open interest, volume, implied volatility and descriptive PCR. "
    "it does not place orders or generate automatic trade instructions."
)

options_left, options_right = st.columns([1, 3])
with options_left:
    options_underlying = st.selectbox(
        "Options underlying",
        ["NIFTY", "BANKNIFTY", "FINNIFTY"],
        key="options_underlying",
    )
    options_load = st.button(
        "Load option chain",
        type="primary",
        key="load_option_chain",
    )
with options_right:
    st.info(
        "Dhan is the primary provider for Indian index option chains. NSE and Yahoo Finance are "
        "used only as fallbacks. EROS shows UNAVAILABLE when no provider supplies "
        "usable data rather than inventing option values."
    )

if options_load:
    with st.spinner(f"Loading {options_underlying} option chain…"):
        st.session_state["options_chain_result"] = fetch_option_chain(options_underlying)

options_result = st.session_state.get("options_chain_result")
if options_result is None:
    st.caption("Select an underlying and load its option chain to begin.")
elif options_result.status == "AVAILABLE":
    expiry_options = list(options_result.expiries)
    expiry = st.selectbox(
        "Expiry",
        expiry_options,
        index=(
            expiry_options.index(options_result.expiry)
            if options_result.expiry in expiry_options
            else 0
        ),
        key="options_expiry",
    )
    if expiry != options_result.expiry and st.button(
        "Reload selected expiry",
        key="reload_option_expiry",
    ):
        with st.spinner(f"Loading {options_underlying} · {expiry}…"):
            st.session_state["options_chain_result"] = fetch_option_chain(
                options_underlying,
                expiry,
            )
        st.rerun()

    metric_left, metric_mid, metric_right = st.columns(3)
    metric_left.metric(
        "Underlying spot",
        f"₹{options_result.spot:,.2f}" if options_result.spot else "—",
    )
    metric_mid.metric("Expiry", options_result.expiry or "—")
    metric_right.metric("Provider", options_result.provider_symbol.split(":")[0])

    option_summary = summarize_option_chain(options_result.chain)
    st.dataframe(option_summary, use_container_width=True, hide_index=True)
    st.dataframe(options_result.chain, use_container_width=True, hide_index=True)
    st.download_button(
        "Download option chain CSV",
        options_result.chain.to_csv(index=False).encode("utf-8"),
        file_name=f"{options_underlying.lower()}_option_chain.csv",
        mime="text/csv",
        key="download_option_chain",
    )
else:
    st.warning(f"Options data: {options_result.status} · {options_result.message}")

left, middle, right = st.columns(3)
with left:
    exchange = st.selectbox(
        "Exchange",
        ["Both", "NSE", "BSE"],
        format_func=lambda value: "NSE + BSE" if value == "Both" else value,
    )
with middle:
    cap_category = st.selectbox(
        "Market-cap basket",
        ["All caps", "Large cap", "Mid cap", "Small cap"],
    )
with right:
    price_limit = st.selectbox(
        "Low-price threshold",
        [10.0, 20.0, 50.0, 100.0],
        index=2,
        format_func=lambda value: f"₹{value:g}",
    )

if exchange == "BSE":
    st.warning(
        "Yahoo Finance identifies BSE (.BO) quotes as delayed by 15 minutes. "
        "NSE (.NS) quotes are listed as real-time. BSE results should therefore "
        "not be treated as real-time intraday data."
    )

lookback = st.selectbox("Momentum window", [2, 3, 5], index=2)

low_price_only = st.checkbox(
    "Show low-price candidates only",
    value=False,
    help="Filter the ranked results to stocks at or below the selected threshold.",
)
limit = st.selectbox("Maximum results", [10, 20, 30, 50], index=1)
min_change = st.slider("Minimum price change (%)", 0.25, 3.0, 0.5, 0.25)
min_volume = st.slider("Minimum volume surge (x)", 1.0, 5.0, 1.2, 0.1)
refresh_left, refresh_right = st.columns(2)
with refresh_left:
    auto_refresh = st.checkbox(
        "Auto-refresh and rescan",
        value=False,
        help="Refreshes the intraday scan at the selected interval during NSE market hours.",
    )
with refresh_right:
    refresh_interval = st.selectbox(
        "Refresh interval",
        list(ALLOWED_REFRESH_SECONDS),
        index=list(ALLOWED_REFRESH_SECONDS).index(DEFAULT_REFRESH_SECONDS),
        format_func=lambda value: f"{value // 60} minute" + ("s" if value != 60 else ""),
    )
exclude_flagged = st.checkbox(
    "Exclude known NSE surveillance flags",
    value=True,
    help=(
        "Removes NSE candidates carrying a known surveillance indicator in the "
        "latest available REG_IND archive. BSE candidates remain marked for manual "
        "review."
    ),
)

# Streamlit fragments provide the lightweight clock that drives the full-app
# rescan only when Live Market Mode is enabled. The market-hours check prevents
# unnecessary scans outside the NSE cash session.
@st.fragment(run_every=60 if auto_refresh else None)
def _live_market_mode_controller():
    now = pd.Timestamp.now(tz="Asia/Kolkata").to_pydatetime()
    if not auto_refresh:
        st.caption("⚪ Live Market Mode: OFF")
        return

    if not market_is_open(now):
        st.info(
            "🔵 Live Market Mode: ARMED · scans are paused outside NSE market hours "
            "(09:15–15:30 IST) and will resume automatically during the next session."
        )
        return

    last_scan = st.session_state.get("intraday_last_scan_at")
    remaining = next_refresh_seconds(last_scan, refresh_interval, now)
    if last_scan is None or remaining <= 0:
        st.session_state["intraday_auto_refresh_pending"] = True
        st.rerun()

    st.success(
        f"🟢 LIVE MARKET MODE · next scan in {refresh_label(remaining)} · "
        f"refresh interval {refresh_interval // 60} min"
    )


_live_market_mode_controller()

scan_requested = st.button("Scan now", type="primary")
auto_scan_requested = st.session_state.pop("intraday_auto_refresh_pending", False)

if scan_requested or auto_scan_requested:
    previous_results = st.session_state.get("day_trader_opportunities")
    with st.spinner("Scanning the current NSE+BSE candidate universe…"):
        results = scan_day_trader_opportunities(
            limit=100,
            exchange_category=exchange,
            cap_category=cap_category,
            max_price=price_limit,
            lookback_minutes=lookback,
            min_change_percent=min_change,
            min_volume_surge=min_volume,
            low_price_only=low_price_only,
        )
    scan_stats = results.attrs.get("scan_stats", {}) if results is not None else {}
    st.session_state["intraday_scan_stats"] = scan_stats
    results = results.head(limit).reset_index(drop=True)
    scan_at = pd.Timestamp.now(tz="Asia/Kolkata")
    st.session_state["intraday_market_regime"] = classify_scan_regime(results)
    snapshot_history = st.session_state.get("intraday_scan_snapshots", [])
    st.session_state["intraday_scan_snapshots"] = record_scan_snapshot(
        snapshot_history,
        results,
        scan_at.to_pydatetime(),
    )
    st.session_state["day_trader_opportunities"] = results
    st.session_state["intraday_last_scan_at"] = scan_at
    if previous_results is not None:
        alerts = detect_intraday_alerts(previous_results, results, scan_at.to_pydatetime())
        alert_history = st.session_state.get("intraday_alert_history", [])
        st.session_state["intraday_alert_history"] = append_alert_history(alert_history, alerts)
    scan_health = assess_scan_health(results, scan_at.to_pydatetime())
    health_history = st.session_state.get("intraday_health_history", [])
    st.session_state["intraday_health_history"] = record_health_observation(
        health_history,
        scan_health,
        scan_at.to_pydatetime(),
    )
    previous_states = st.session_state.get("intraday_setup_states", {})
    updated_states, transitions = record_setup_state_transitions(
        previous_states,
        results,
        pd.Timestamp.now(tz="Asia/Kolkata").to_pydatetime(),
    )
    st.session_state["intraday_setup_states"] = updated_states
    previous_monitor = st.session_state.get("intraday_setup_monitor", {})
    st.session_state["intraday_setup_monitor"] = record_setup_observations(
        previous_monitor,
        results,
        pd.Timestamp.now(tz="Asia/Kolkata").to_pydatetime(),
    )
    previous_outcomes = st.session_state.get("intraday_setup_outcomes", {})
    st.session_state["intraday_setup_outcomes"] = record_setup_outcomes(
        previous_outcomes,
        results,
        pd.Timestamp.now(tz="Asia/Kolkata").to_pydatetime(),
    )
    previous_windows = st.session_state.get("intraday_multi_window_outcomes", {})
    st.session_state["intraday_multi_window_outcomes"] = record_multi_window_outcomes(
        previous_windows,
        results,
        pd.Timestamp.now(tz="Asia/Kolkata").to_pydatetime(),
    )
    history = st.session_state.get("intraday_state_transitions", [])
    st.session_state["intraday_state_transitions"] = transitions + history

raw_results = st.session_state.get("day_trader_opportunities")
last_scan_at = st.session_state.get("intraday_last_scan_at")
if last_scan_at is not None:
    st.caption(f"Last scan: {pd.Timestamp(last_scan_at).strftime('%d %b %Y, %H:%M:%S IST')}")

health = assess_scan_health(
    raw_results,
    pd.Timestamp(last_scan_at).to_pydatetime() if last_scan_at is not None else None,
)
if health["status"] == "HEALTHY":
    st.success(f"Data health: {health['message']}")
elif health["status"] == "STALE":
    st.warning(f"Data health: {health['message']} Re-scan before reviewing candidates.")
elif health["status"] != "NO_SCAN":
    st.warning(f"Data health: {health['message']}")

market_regime = st.session_state.get("intraday_market_regime", {})
if market_regime:
    st.subheader("Observed intraday market regime")
    st.caption(
        "Descriptive breadth and volume context from the latest completed scan; "
        "not a forecast."
    )
    st.dataframe(pd.DataFrame([market_regime]), use_container_width=True, hide_index=True)

exchange_pulse = exchange_summary(raw_results)
st.subheader("NSE / BSE intraday pulse")
st.caption(
    "Descriptive exchange-level metrics from the latest completed scan. "
    "They summarize observed data and are not forecasts."
)
if exchange_pulse.empty:
    st.caption("Run a scan with both exchanges selected to populate the exchange pulse.")
else:
    st.dataframe(exchange_pulse, use_container_width=True, hide_index=True)
@st.fragment(run_every=60 if auto_refresh else None, key="price_jump_watchlist")
def _price_jump_watchlist():
    price_jump_col, price_jump_status = st.columns([4, 1])
    with price_jump_col:
        st.subheader("⚡ Intraday Price-Jump Pulse")
        st.caption(
            "Scans the maintained NSE/BSE candidate universe for short-window price jumps and relative volume. "
            "This is a retrospective screen using Yahoo Finance candles, not a tick-level alert or trade instruction."
        )
    with price_jump_status:
        if st.session_state.get("price_jump_scan_time"):
            st.caption(f"Last pulse: {st.session_state['price_jump_scan_time']}")

    jump_left, jump_mid, jump_right, jump_action = st.columns(4)
    with jump_left:
        jump_exchange = st.selectbox(
            "Pulse exchange",
            ["Both", "NSE", "BSE"],
            format_func=lambda value: "NSE + BSE" if value == "Both" else value,
            key="pulse_exchange",
        )
    with jump_mid:
        jump_cap = st.selectbox(
            "Pulse market-cap basket",
            ["All caps", "Large cap", "Mid cap", "Small cap"],
            key="pulse_cap",
        )
    with jump_right:
        jump_window = st.selectbox(
            "Pulse window",
            [1, 2, 3, 5, 10],
            index=0,
            format_func=lambda value: f"{value} minutes",
            key="pulse_window",
        )
    with jump_action:
        jump_threshold = st.selectbox(
            "Minimum jump",
            [0.5, 1.0, 1.5, 2.0],
            index=1,
            format_func=lambda value: f"{value:.1f}%",
            key="pulse_threshold",
        )

    if auto_refresh:
        st.caption(
            "🟢 Live Price-Jump Watchlist: refreshes every 1 minute during NSE market hours. "
            "The selected price-jump window is evaluated on each refresh."
        )

    pulse_scan = st.button("Run Price-Jump Pulse", type="primary", key="run_price_jump_pulse")
    should_auto_scan = auto_refresh and market_is_open(
        pd.Timestamp.now(tz="Asia/Kolkata").to_pydatetime()
    )
    active_job_id = st.session_state.get("price_jump_scan_job_id")

    if (pulse_scan or should_auto_scan) and not active_job_id:
        active_job_id = _SCAN_MANAGER.start_price_jump_scan(
            limit=30,
            cap_category=jump_cap,
            exchange_category=jump_exchange,
            lookback_minutes=jump_window,
            jump_percent=jump_threshold,
        )
        st.session_state["price_jump_scan_job_id"] = active_job_id
        st.info(
            "⏳ Price-Jump Pulse started in the background. The page remains responsive while "
            "market data loads."
        )
        st.rerun()

    active_job_id = st.session_state.get("price_jump_scan_job_id")
    if active_job_id:
        job = _SCAN_MANAGER.get_job(active_job_id)
        if job is None:
            st.session_state.pop("price_jump_scan_job_id", None)
            st.error("Background price-jump scan was lost. Please run the pulse again.")
        elif job["status"] in {"queued", "running"}:
            st.info(
                "⏳ Price-Jump Pulse is still running in the background. Results will appear "
                "automatically."
            )
        elif job["status"] == "failed":
            st.session_state.pop("price_jump_scan_job_id", None)
            st.error(
                f"Price-jump pulse could not complete: {job.get('error') or 'unknown error'}"
            )
        elif job["status"] == "completed":
            pulse_results = pd.DataFrame(job.get("results", []))
            pulse_results.attrs["scan_stats"] = dict(job.get("scan_stats", {}))
            pulse_at = pd.Timestamp(job["finished_at"])
            previous_watchlist = st.session_state.get("price_jump_top10_watchlist")
            current_watchlist = pulse_results.head(10).copy()
            current_watchlist.insert(0, "Rank", range(1, len(current_watchlist) + 1))
            st.session_state["price_jump_watchlist_delta"] = compare_watchlists(
                previous_watchlist,
                current_watchlist,
            )
            st.session_state["price_jump_top10_watchlist"] = current_watchlist
            st.session_state["price_jump_results"] = pulse_results
            st.session_state["price_jump_scan_time"] = pulse_at.tz_convert(
                "Asia/Kolkata"
            ).strftime("%d %b %Y, %H:%M:%S IST")
            st.session_state["price_jump_scan_stats"] = dict(job.get("scan_stats", {}))
            st.session_state["price_jump_scan_window"] = jump_window
            st.session_state["price_jump_history"] = append_price_jump_snapshot(
                st.session_state.get("price_jump_history"),
                pulse_at.to_pydatetime(),
                pulse_results,
            )
            st.session_state.pop("price_jump_scan_job_id", None)
            st.success(
                f"✅ Price-Jump Pulse completed · {len(pulse_results)} candidates returned."
            )
    pulse_results = st.session_state.get("price_jump_results")
    if pulse_results is None:
        st.info(
            "Run the Price-Jump Pulse during market hours to populate short-window momentum candidates."
        )
    elif pulse_results.empty:
        st.info(
            "No candidates met the selected threshold, or the provider returned insufficient candles. "
            "Try a lower threshold or another window during market hours."
        )
    else:
        pulse_columns = [
            column
            for column in [
                "Symbol",
                "Exchange",
                "Market-cap basket",
                "Last price",
                f"Change over {st.session_state.get('price_jump_scan_window', jump_window)} min %",
                "Day %",
                "RVOL",
                "Latest candle (provider time)",
            ]
            if column in pulse_results.columns
        ]
        st.dataframe(pulse_results[pulse_columns], use_container_width=True, hide_index=True)

        st.subheader("⭐ Top 10 Price-Jump Watchlist")
        if st.session_state.get("price_jump_scan_window") == 1:
            st.caption(
                "The watchlist shows the 10 largest observed 1-minute price jumps from the "
                "latest pulse, ranked by percentage change and then relative volume. "
                "With Live Market Mode enabled, it refreshes every 60 seconds during NSE "
                "market hours. It is a monitoring list, not a trade recommendation."
            )
        else:
            st.caption(
                "The watchlist keeps the 10 largest observed short-window price jumps from the "
                "latest pulse, ranked by percentage change and then relative volume. "
                "It is a monitoring list, not a trade recommendation."
            )
        watchlist = pulse_results.head(10).copy()
        watchlist.insert(0, "Rank", range(1, len(watchlist) + 1))
        watchlist_columns = [
            column
            for column in [
                "Rank",
                "Symbol",
                "Exchange",
                "Last price",
                f"Change over {st.session_state.get('price_jump_scan_window', jump_window)} min %",
                "Day %",
                "RVOL",
                "Latest candle (provider time)",
            ]
            if column in watchlist.columns
        ]
        st.dataframe(
            watchlist[watchlist_columns],
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "Download top-10 watchlist CSV",
            watchlist[watchlist_columns].to_csv(index=False).encode("utf-8"),
            file_name="top10_price_jump_watchlist.csv",
            mime="text/csv",
            key="download_top10_price_jump_watchlist",
        )

        watchlist_delta = st.session_state.get("price_jump_watchlist_delta")
        if watchlist_delta is not None and not watchlist_delta.empty:
            st.subheader("🔄 Watchlist changes since previous refresh")
            st.caption(
                "Descriptive changes versus the immediately previous Top-10 pulse: "
                "NEW entrants, UP/DOWN rank movements, unchanged names and DROPPED names."
            )
            st.dataframe(
                watchlist_delta,
                use_container_width=True,
                hide_index=True,
            )
        elif st.session_state.get("price_jump_top10_watchlist") is not None:
            st.caption("Watchlist change tracking starts after the next completed pulse.")

    pulse_stats = st.session_state.get("price_jump_scan_stats", {})
    if pulse_stats:
        st.caption(
            f"Candidates checked: {pulse_stats.get('candidate_count', 0)} · "
            f"Usable candles: {pulse_stats.get('usable_count', 0)} · "
            f"Matches before limit: {pulse_stats.get('matches_before_limit', 0)} · "
            f"Interval: {pulse_stats.get('interval', '—')}"
        )

    price_jump_history = st.session_state.get("price_jump_history")
    if price_jump_history is not None and not price_jump_history.empty:
        pulse_history = summarize_price_jump_history(price_jump_history)
        if not pulse_history.empty:
            st.caption(
                "Repeated observations in this Streamlit session show price-jump persistence "
                "by symbol and exchange."
            )
            st.dataframe(pulse_history.head(20), use_container_width=True, hide_index=True)


_price_jump_watchlist()
snapshots = snapshot_frame(st.session_state.get("intraday_scan_snapshots", []))
st.subheader("Intraday scan history")
st.caption(
    "Session-local snapshots show how the scanner's observed candidate set changes between scans."
)
if snapshots.empty:
    st.caption("No completed scan snapshots are available yet.")
else:
    st.dataframe(snapshots.tail(50), use_container_width=True, hide_index=True)
    st.download_button(
        "Download scan snapshot history CSV",
        snapshots.to_csv(index=False).encode("utf-8"),
        file_name="intraday_scan_snapshot_history.csv",
        mime="text/csv",
    )

snapshot_deltas = snapshot_delta_frame(st.session_state.get("intraday_scan_snapshots", []))
st.subheader("Intraday scan changes")
st.caption(
    "Descriptive changes versus the previous completed scan, including candidate breadth "
    "and top-symbol turnover."
)
if snapshot_deltas.empty:
    st.caption("Run at least two completed scans to populate scan-change history.")
else:
    st.dataframe(snapshot_deltas, use_container_width=True, hide_index=True)
    st.download_button(
        "Download scan change history CSV",
        snapshot_deltas.to_csv(index=False).encode("utf-8"),
        file_name="intraday_scan_change_history.csv",
        mime="text/csv",
    )

alert_history = alert_history_frame(st.session_state.get("intraday_alert_history", []))
st.subheader("Intraday change alerts")
st.caption(
    "Alerts describe changes between completed scans in this session. "
    "They are observational notifications, not trade instructions or predictions."
)
if alert_history.empty:
    st.caption("No changes have been detected between scans yet.")
else:
    st.dataframe(alert_history.head(100), use_container_width=True, hide_index=True)
    st.download_button(
        "Download intraday alert history CSV",
        alert_history.to_csv(index=False).encode("utf-8"),
        file_name="intraday_alert_history.csv",
        mime="text/csv",
    )

journal = journal_frame(st.session_state.get("intraday_trade_journal", []))
st.subheader("Intraday trade journal")
st.caption(
    "Record paper trades or completed trades for review. Journal calculations are descriptive "
    "and do not place orders or recommend a trade."
)
with st.form("intraday_trade_journal_form", clear_on_submit=True):
    journal_left, journal_mid, journal_right = st.columns(3)
    with journal_left:
        journal_symbol = st.text_input("Symbol")
        journal_exchange = st.selectbox("Journal exchange", ["NSE", "BSE"])
        journal_side = st.selectbox("Side", ["LONG", "SHORT"])
        journal_setup = st.text_input("Setup", value="Intraday setup")
        journal_entry = st.number_input("Entry price", min_value=0.0, value=0.0, step=0.05)
    with journal_mid:
        journal_stop = st.number_input("Stop loss", min_value=0.0, value=0.0, step=0.05)
        journal_target = st.number_input("Target", min_value=0.0, value=0.0, step=0.05)
        journal_exit = st.number_input(
            "Exit price (0 = still open)",
            min_value=0.0,
            value=0.0,
            step=0.05,
        )
        journal_quantity = st.number_input(
            "Quantity",
            min_value=1,
            value=1,
            step=1,
        )
    with journal_right:
        journal_reason = st.text_area("Reason for entry")
        journal_lesson = st.text_area("Lesson / review note")
        journal_submit = st.form_submit_button("Add journal entry", type="primary")

if journal_submit:
    if not journal_symbol.strip() or journal_entry <= 0 or journal_stop <= 0 or journal_target <= 0:
        st.error("Enter symbol, entry, stop loss and target before saving the journal entry.")
    elif journal_side == "LONG" and not (journal_stop < journal_entry < journal_target):
        st.error("For a LONG journal entry, use stop loss < entry < target.")
    elif journal_side == "SHORT" and not (journal_target < journal_entry < journal_stop):
        st.error("For a SHORT journal entry, use target < entry < stop loss.")
    else:
        exit_price = journal_exit if journal_exit > 0 else None
        history = st.session_state.get("intraday_trade_journal", [])
        st.session_state["intraday_trade_journal"] = add_trade(
            history,
            timestamp=pd.Timestamp.now(tz="Asia/Kolkata").to_pydatetime(),
            symbol=journal_symbol,
            exchange=journal_exchange,
            side=journal_side,
            setup=journal_setup,
            entry=journal_entry,
            stop_loss=journal_stop,
            target=journal_target,
            exit_price=exit_price,
            quantity=journal_quantity,
            reason=journal_reason,
            lesson=journal_lesson,
        )
        st.rerun()

journal_summary_frame = journal_summary(st.session_state.get("intraday_trade_journal", []))
st.dataframe(journal_summary_frame, use_container_width=True, hide_index=True)
if journal.empty:
    st.caption("No journal entries recorded in this session yet.")
else:
    st.dataframe(journal.head(100), use_container_width=True, hide_index=True)
    st.download_button(
        "Download trade journal CSV",
        journal.to_csv(index=False).encode("utf-8"),
        file_name="intraday_trade_journal.csv",
        mime="text/csv",
    )

trade_history = st.session_state.get("intraday_trade_journal", [])
performance = performance_summary(trade_history)
setup_stats = setup_performance(trade_history)
side_stats = side_performance(trade_history)

st.subheader("Trade performance analytics")
st.caption(
    "Descriptive statistics from journaled closed trades. They summarize recorded history "
    "and are not a forecast of future performance."
)
st.dataframe(performance, use_container_width=True, hide_index=True)
if not setup_stats.empty:
    st.dataframe(setup_stats, use_container_width=True, hide_index=True)
if not side_stats.empty:
    st.dataframe(side_stats, use_container_width=True, hide_index=True)

health_history = health_history_frame(st.session_state.get("intraday_health_history", []))
st.subheader("Intraday scan health history")
st.caption(
    "This session-local history records the descriptive health state of each completed scan. "
    "It does not assess trade quality or predict market outcomes."
)
if health_history.empty:
    st.caption("No completed scan health observations are available yet.")
else:
    st.dataframe(health_history.head(50), use_container_width=True, hide_index=True)
    st.download_button(
        "Download scan health history CSV",
        health_history.to_csv(index=False).encode("utf-8"),
        file_name="intraday_scan_health_history.csv",
        mime="text/csv",
    )

if raw_results is None:
    st.info("Run a scan during market hours to populate the opportunity table.")
elif raw_results.empty:
    scan_stats = st.session_state.get("intraday_scan_stats", {})
    st.warning(
        "No candidates met the selected conditions. The diagnostics below show whether "
        "the cause is missing intraday data or the selected filters."
    )
    if scan_stats:
        diagnostics = {
            "Candidate universe": scan_stats.get("candidate_count", 0),
            "Symbols attempted": scan_stats.get("attempted_count", 0),
            "Usable intraday data": scan_stats.get("usable_data_count", 0),
            "Strategy data available": scan_stats.get("strategy_count", 0),
            "Price-change filter pass": scan_stats.get("price_change_pass_count", 0),
            "Volume-surge filter pass": scan_stats.get("volume_surge_pass_count", 0),
            "Both filters pass": scan_stats.get("both_filters_pass_count", 0),
            "Low-price threshold pass": scan_stats.get("low_price_pass_count", 0),
            "Matches before safety": scan_stats.get("matches_before_safety", 0),
            "Matches after safety": scan_stats.get("matches_after_safety", 0),
            "Data interval": scan_stats.get("interval", "—"),
            "Exchange": scan_stats.get("exchange", "—"),
            "Market-cap basket": scan_stats.get("cap_category", "—"),
        }
        st.subheader("Scan diagnostics")
        st.dataframe(
            pd.DataFrame([diagnostics]),
            use_container_width=True,
            hide_index=True,
        )
else:
    results = raw_results.copy()
    scan_stats = st.session_state.get("intraday_scan_stats", {})
    if scan_stats:
        st.caption(
            f"Scan: {scan_stats.get('attempted_count', 0)} attempted • "
            f"{scan_stats.get('usable_data_count', 0)} usable • "
            f"{scan_stats.get('matches_before_safety', 0)} matched filters"
        )
    if "Latest candle" in results.columns:
        observed = pd.to_datetime(results["Latest candle"], errors="coerce").dropna()
        if not observed.empty:
            status = describe_market_status(observed.max())
            st.info(f"**{status['label']}**\n\n{status['message']}")
    if exclude_flagged and "Safety flags" in results.columns:
        results = results[results["Safety flags"].fillna("").eq("")].copy()

    quality_summary = dashboard_summary(
        st.session_state.get("intraday_setup_states", {}),
        st.session_state.get("intraday_setup_monitor", {}),
        st.session_state.get("intraday_setup_outcomes", {}),
        st.session_state.get("intraday_state_transitions", []),
        st.session_state.get("intraday_multi_window_outcomes", {}),
    )

    filter_left, filter_mid, filter_right = st.columns(3)
    with filter_left:
        live_direction = st.selectbox(
            "Live direction filter",
            ["All", "LONG", "SHORT", "NEUTRAL"],
        )
    with filter_mid:
        live_state_options = ["All"]
        if "Plan state" in results.columns:
            live_state_options.extend(sorted(results["Plan state"].dropna().astype(str).unique()))
        live_state = st.selectbox("Live setup-state filter", live_state_options)
    with filter_right:
        live_exchange_options = ["All"]
        if "Exchange" in results.columns:
            live_exchange_options.extend(sorted(results["Exchange"].dropna().astype(str).unique()))
        live_exchange = st.selectbox("Live exchange filter", live_exchange_options)
    risk_left, risk_right = st.columns(2)
    with risk_left:
        risk_budget = st.number_input(
            "Risk budget per candidate (₹)",
            min_value=0.0,
            value=1000.0,
            step=100.0,
        )
    with risk_right:
        capital_limit = st.number_input(
            "Capital limit per candidate (₹)",
            min_value=0.0,
            value=100000.0,
            step=5000.0,
        )
    minimum_live_score = st.slider(
        "Minimum composite score",
        0.0,
        100.0,
        0.0,
        5.0,
        help="Filters the latest scan; it does not create a new score or predict returns.",
    )
    filtered_results = filter_intraday_candidates(
        results,
        direction=live_direction,
        setup_state=live_state,
        exchange=live_exchange,
        minimum_score=minimum_live_score,
        limit=limit,
    )
    scored_results = scorecard_frame(filtered_results)
    if not scored_results.empty:
        filtered_results = scored_results

    risk_results = risk_plan_frame(
        filtered_results,
        risk_budget=risk_budget,
        capital_limit=capital_limit,
    )

    with st.expander("Position sizing calculator", expanded=False):
        size_left, size_mid, size_right = st.columns(3)
        with size_left:
            sizing_capital = st.number_input(
                "Sizing capital (₹)",
                min_value=0.0,
                value=100000.0,
                step=5000.0,
                key="sizing_capital",
            )
            sizing_risk = st.number_input(
                "Risk per trade (%)",
                min_value=0.0,
                max_value=100.0,
                value=1.0,
                step=0.25,
                key="sizing_risk",
            )
        with size_mid:
            sizing_entry = st.number_input(
                "Sizing entry",
                min_value=0.0,
                value=0.0,
                step=0.05,
                key="sizing_entry",
            )
            sizing_stop = st.number_input(
                "Sizing stop loss",
                min_value=0.0,
                value=0.0,
                step=0.05,
                key="sizing_stop",
            )
        with size_right:
            sizing_target = st.number_input(
                "Sizing target",
                min_value=0.0,
                value=0.0,
                step=0.05,
                key="sizing_target",
            )
            sizing_side = st.selectbox(
                "Sizing side",
                ["LONG", "SHORT"],
                key="sizing_side",
            )
        if sizing_entry > 0 and sizing_stop > 0 and sizing_target > 0:
            sizing_result = calculate_position_size(
                sizing_capital,
                sizing_risk,
                sizing_entry,
                sizing_stop,
                sizing_target,
                sizing_side,
            )
            st.caption(
                "Position size is a planning calculation from capital, risk and reference levels. "
                "It does not place orders."
            )
            st.dataframe(
                pd.DataFrame(
                    [{
                        "Risk budget": sizing_result.risk_amount,
                        "Risk/share": sizing_result.risk_per_share,
                        "Risk quantity": sizing_result.risk_quantity,
                        "Capital quantity": sizing_result.capital_quantity,
                        "Planned quantity": sizing_result.quantity,
                        "Planned capital": sizing_result.planned_capital,
                        "Planned risk": sizing_result.planned_risk,
                        "Planned reward": sizing_result.planned_reward,
                        "Planned R:R": sizing_result.planned_rr,
                    }]
                ),
                use_container_width=True,
                hide_index=True,
            )
    st.subheader("Intraday quality dashboard")
    st.caption(
        "Consolidated session metrics from the observed setup history. "
        "These metrics describe the current session and do not predict future returns."
    )
    st.dataframe(quality_summary, use_container_width=True, hide_index=True)

    validation = build_signal_validation_frame(
        st.session_state.get("intraday_setup_outcomes", {}),
        st.session_state.get("intraday_multi_window_outcomes", {}),
        results,
    )
    validation_summary_frame = validation_summary(validation)
    st.subheader("Intraday signal validation")
    st.caption(
        "Consolidates observed setup outcomes with completed 5m, 10m, 15m and 30m "
        "windows. Positive and negative labels describe recorded movement from the "
        "first observed setup state; they are not predictions or trade recommendations."
    )
    summary_columns = st.columns(5)
    summary_values = dict(
        zip(
            validation_summary_frame["Metric"],
            validation_summary_frame["Value"],
            strict=True,
        )
    )
    for column, metric in zip(
        summary_columns,
        ["Tracked setups", "Positive", "Negative", "Flat", "Unresolved"],
        strict=True,
    ):
        column.metric(metric, int(summary_values.get(metric, 0)))
    if validation.empty:
        st.caption("No observed setup outcomes are available for validation yet.")
    else:
        st.dataframe(validation.head(50), use_container_width=True, hide_index=True)
        st.download_button(
            "Download signal validation CSV",
            validation.to_csv(index=False).encode("utf-8"),
            file_name="intraday_signal_validation.csv",
            mime="text/csv",
        )

    st.subheader("Current opportunity candidates")
    state_counts = (
        filtered_results["Plan state"].value_counts()
        if "Plan state" in filtered_results.columns
        else pd.Series(dtype="int64")
    )
    if not state_counts.empty:
        st.caption(
            "Setup state is a snapshot of the latest observed price versus the calculated "
            "reference levels; it is not a prediction of future price movement."
        )
        metrics = st.columns(min(4, len(state_counts)))
        for column, (state, count) in zip(metrics, state_counts.head(4).items(), strict=False):
            column.metric(str(state), int(count))
    preferred_columns = [
        "Symbol",
        "Exchange",
        "Market-cap basket",
        "Price",
        "5-min change %",
        "Volume surge x",
        "Day-trading setup",
        "Direction",
        "Setup state",
        "Composite score",
        "Setup Total",
        "Setup Trend",
        "Setup Volume",
        "Setup VWAP",
        "Setup Momentum",
        "Setup Breakout",
        "Setup Session",
        "RVOL",
        "Trend",
        "VWAP",
        "VWAP price",
        "VWAP distance %",
        "VWAP bias",
        "ORB 5m high",
        "ORB 5m low",
        "ORB 5m state",
        "ORB 15m high",
        "ORB 15m low",
        "ORB 15m state",
        "EMA 9/20",
        "Evidence",
        "Plan",
        "Plan state",
        "Entry reference",
        "Stop reference",
        "Target 1",
        "Target 2",
        "Target 3",
        "R:R T1",
        "R:R T2",
        "R:R T3",
        "Breakout",
        "Strategy breakdown",
        "Liquidity",
    ]
    if filtered_results.empty:
        st.warning(
            "No candidates match the current live filters. "
            "Uncheck the filter only if you intend to review the flagged names separately."
        )
    else:
        display_columns = [column for column in preferred_columns if column in results.columns]
        risk_columns = display_columns + [
            column
            for column in [
                "Risk-based quantity",
                "Capital-based quantity",
                "Suggested quantity",
                "Planned capital",
                "Planned risk",
            ]
            if column in risk_results.columns
        ]
        st.dataframe(
            risk_results[risk_columns],
            use_container_width=True,
            hide_index=True,
        )
    st.download_button(
        "Download opportunity CSV",
        risk_results.to_csv(index=False).encode("utf-8"),
        file_name="day_trader_opportunities.csv",
        mime="text/csv",
    )

    transition_history = transitions_frame(st.session_state.get("intraday_state_transitions", []))
    st.subheader("Intraday setup state changes")
    if transition_history.empty:
        st.caption("No setup-state changes have been observed in this session yet.")
    else:
        st.dataframe(transition_history.head(50), use_container_width=True, hide_index=True)
        st.download_button(
            "Download state-change history CSV",
            transition_history.to_csv(index=False).encode("utf-8"),
            file_name="intraday_setup_state_changes.csv",
            mime="text/csv",
        )

    monitor = monitor_frame(
        st.session_state.get("intraday_setup_monitor", {}),
        pd.Timestamp.now(tz="Asia/Kolkata").to_pydatetime(),
    )
    st.subheader("Intraday setup monitoring")
    st.caption(
        "This view shows how long each observed setup has persisted in this Streamlit session. "
        "It records observations; it does not predict future price movement."
    )
    if monitor.empty:
        st.caption("No setup observations are available yet.")
    else:
        st.dataframe(monitor.head(50), use_container_width=True, hide_index=True)
        st.download_button(
            "Download setup monitoring CSV",
            monitor.to_csv(index=False).encode("utf-8"),
            file_name="intraday_setup_monitoring.csv",
            mime="text/csv",
        )

    outcomes = outcomes_frame(st.session_state.get("intraday_setup_outcomes", {}))
    statistics = setup_statistics(st.session_state.get("intraday_setup_outcomes", {}))
    regime = regime_statistics(st.session_state.get("intraday_setup_outcomes", {}))
    st.subheader("Observed setup outcomes")
    st.caption(
        "Price change is measured from the first observation of the current setup state. "
        "It describes observed movement and is not a forecast or performance guarantee."
    )
    if outcomes.empty:
        st.caption("No repeated setup observations are available yet.")
    else:
        st.dataframe(outcomes.head(50), use_container_width=True, hide_index=True)
        st.download_button(
            "Download setup outcome CSV",
            outcomes.to_csv(index=False).encode("utf-8"),
            file_name="intraday_setup_outcomes.csv",
            mime="text/csv",
        )

    window_outcomes = multi_window_frame(st.session_state.get("intraday_multi_window_outcomes", {}))
    st.subheader("Multi-window setup outcomes")
    st.caption(
        "Observed price change is measured from the start of the current setup state. "
        "A window is filled when a later scan reaches that elapsed time."
    )
    if window_outcomes.empty:
        st.caption("No multi-window observations are available yet.")
    else:
        st.dataframe(window_outcomes.head(50), use_container_width=True, hide_index=True)
        st.download_button(
            "Download multi-window outcome CSV",
            window_outcomes.to_csv(index=False).encode("utf-8"),
            file_name="intraday_multi_window_outcomes.csv",
            mime="text/csv",
        )

    st.subheader("Setup evaluation statistics")
    st.caption(
        "These statistics summarize observed session outcomes by setup state. "
        "They are descriptive and are not a prediction or guarantee of future returns."
    )
    if statistics.empty:
        st.caption("Not enough observed outcomes for statistics yet.")
    else:
        st.dataframe(statistics, use_container_width=True, hide_index=True)
        st.download_button(
            "Download setup statistics CSV",
            statistics.to_csv(index=False).encode("utf-8"),
            file_name="intraday_setup_statistics.csv",
            mime="text/csv",
        )

    st.subheader("Session-phase setup analysis")
    st.caption(
        "Observed outcomes are grouped by the session phase in which the setup state "
        "was first observed. This is descriptive session context, not a prediction."
    )
    if regime.empty:
        st.caption("Not enough observations for session-phase analysis yet.")
    else:
        st.dataframe(regime, use_container_width=True, hide_index=True)
        st.download_button(
            "Download session-phase statistics CSV",
            regime.to_csv(index=False).encode("utf-8"),
            file_name="intraday_session_phase_statistics.csv",
            mime="text/csv",
        )

    st.caption(
        "Entry, stop and target columns are conditional reference levels calculated from "
        "the current setup, support/resistance and ATR. They are not guaranteed execution "
        "levels and should be rechecked against live market data. "
    )
    st.caption(
        "Composite score combines the existing opportunity score with the book-based "
        "day-trading setup score. Higher scores describe more observed conditions; they "
        "do not imply a higher probability of profit. "
    )
    st.caption(
        "Opportunity score is descriptive: momentum 35%, volume surge 30%, session "
        "range 20%, breakout condition 15%. A higher score does not imply a higher "
        "probability of profit."
    )
    st.caption(
        "Safety status is a screening aid, not a clearance. NSE flags come from the "
        "latest available REG_IND archive; BSE candidates require a separate exchange check."
    )



st.divider()
st.subheader("Risk and data checks")
st.markdown("""
- Verify the latest candle timestamp before acting; Yahoo Finance may be delayed or incomplete.
- The safety filter checks the latest available NSE surveillance indicator archive (ASM/GSM/ESM and Trade-to-Trade where reported).
- Price bands, bid/ask spreads and BSE surveillance status still require broker/exchange confirmation.
- NSE surveillance measures can change after the archive snapshot; re-check before placing an order.
- Low price is not the same as low risk. A ₹10 stock can be substantially harder to trade than a liquid higher-priced stock.
- The scanner does not calculate guaranteed entries, targets or stop-losses and does not place trades.
""")
st.caption(
    "Use the results as candidates for further chart/order-book review and paper trading, "
    "not as guaranteed money-making selections."
)
