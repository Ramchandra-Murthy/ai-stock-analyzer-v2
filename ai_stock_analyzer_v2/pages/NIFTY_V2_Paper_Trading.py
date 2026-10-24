"""Streamlit dashboard for simulation-only NIFTY Options V2 paper trading."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime, time
from io import StringIO
from zoneinfo import ZoneInfo

import streamlit as st

from engine.nifty_options_v2_auto import NiftyOptionsV2AutoPaper
from engine.nifty_options_v2_auto_cycle import NiftyOptionsV2AutoCycle
from engine.nifty_options_v2_cycle_status import cycle_status
from engine.nifty_options_v2_freshness import market_data_is_fresh
from engine.nifty_options_v2_live import (
    LivePaperObservation,
    NiftyOptionsV2LivePaperSession,
)
from engine.nifty_options_v2_market_data import (
    NiftyV2MarketObservation,
    select_deepest_itm_call,
)
from engine.nifty_options_v2_market_session import market_session_ready
from engine.nifty_options_v2_provider_guard import provider_data_ready
from engine.nifty_options_v2_refresh import is_market_hours, refresh_seconds
from services.options_analytics import fetch_option_chain, fetch_option_chain_cached
from strategy.nifty_options_v2 import NiftyCallContract

st.set_page_config(page_title="NIFTY V2 Paper Trading", page_icon="📈", layout="wide")

st.title("NIFTY Options V2 — Paper Trading")

st.warning(
    "PAPER TRADING ONLY — no broker orders are submitted. "
    "Verify market data before acting on any paper decision."
)
st.caption(
    "Simulation only. Live observations refresh during NSE market hours. "
    "This page never submits broker orders."
)

if "nifty_v2_paper_session" not in st.session_state:
    st.session_state.nifty_v2_paper_session = NiftyOptionsV2LivePaperSession()
if "nifty_v2_decision_history" not in st.session_state:
    st.session_state.nifty_v2_decision_history = []

session: NiftyOptionsV2LivePaperSession = st.session_state.nifty_v2_paper_session


@st.fragment(run_every=f"{refresh_seconds()}s")
def show_live_observation() -> None:
    """Refresh the current NIFTY option observation without placing orders."""
    now = datetime.now().astimezone()
    if not is_market_hours(now):
        st.info("NSE market is outside configured market hours. Paper refresh is paused.")
        return

    try:
        result = fetch_option_chain_cached("NIFTY")
        if result.status != "AVAILABLE" or result.spot is None or result.expiry is None:
            st.warning(f"Live option data unavailable: {result.message}")
            return

        expiry = date.fromisoformat(result.expiry)
        selected = select_deepest_itm_call(
            result.chain,
            spot=result.spot,
            expiry=expiry,
            observed_date=now.date(),
        )
        st.metric("NIFTY Spot", f"{result.spot:.2f}")
        st.metric(
            f"Selected ITM CALL {selected.contract.strike:.0f}",
            f"{selected.observation.ltp:.2f}",
        )

        active = session.trader.active_trade
        if active is not None:
            current_ltp = selected.observation.ltp
            st.metric(
                "Paper Unrealized P&L",
                f"{current_ltp - active.entry_ltp:+.2f} points",
            )
    except (ValueError, RuntimeError) as exc:
        st.warning(f"Live refresh failed: {exc}")


show_live_observation()

with st.expander("Manual paper controls"):
    expiry = st.date_input("Option expiry", value=date.today(), key="nifty_v2_manual_expiry")
    strike = st.number_input("CALL strike", min_value=1.0, value=25000.0, step=50.0)
    observed_date = st.date_input(
        "Observation date", value=date.today(), key="nifty_v2_manual_observation_date"
    )
if st.button("Reset Paper Session"):
    st.session_state.nifty_v2_paper_session = NiftyOptionsV2LivePaperSession()
    st.rerun()

india_now = datetime.now(ZoneInfo("Asia/Kolkata"))
market_open = india_now.weekday() < 5 and time(9, 15) <= india_now.time() <= time(15, 30)

st.subheader("NSE Market Session")
if market_open:
    st.success(f"MARKET SESSION OPEN — {india_now.strftime('%H:%M:%S')} IST")
else:
    st.info(f"MARKET SESSION CLOSED — {india_now.strftime('%H:%M:%S')} IST")
st.caption(
    "Session check uses weekday and 09:15–15:30 IST only; "
    "exchange holidays are not inferred here."
)

provider = fetch_option_chain_cached("NIFTY")
provider_fetched_at = datetime.now(UTC)

st.subheader("Market Data Status")
status_left, status_mid, status_right = st.columns(3)
status_left.metric("Provider", provider.provider_symbol)
status_mid.metric("Data Status", provider.status)
status_right.metric("Spot", f"{provider.spot:.2f}" if provider.spot is not None else "Unavailable")
st.caption(provider.message)
st.caption(f"Fetched at (UTC): {provider_fetched_at.isoformat(timespec='seconds')}")
if provider.expiry is not None:
    st.caption(f"Provider-selected expiry: {provider.expiry}")
active = session.trader.active_trade
active_expiry = active.contract.expiry if active is not None else None

cycle = cycle_status(
    expiries=provider.expiries,
    observed_date=india_now.date(),
    active_contract_expiry=active_expiry,
)
auto_cycle = NiftyOptionsV2AutoCycle(auto_paper=NiftyOptionsV2AutoPaper(session=session))
auto_strike = st.checkbox("Automatically select deepest ITM CALL from option chain", value=True)

st.subheader("Automatic Cycle Readiness")
readiness_left, readiness_right = st.columns(2)
cycle_ready = provider.status == "AVAILABLE" and not provider.chain.empty and cycle is not None
readiness_left.metric("Ready", "YES" if cycle_ready else "NO")
if cycle_ready:
    readiness_right.success("Provider data and monthly cycle are available.")
elif provider.status != "AVAILABLE":
    readiness_right.warning("Not ready: provider market data is unavailable.")
elif provider.chain.empty:
    readiness_right.warning("Not ready: provider option chain is empty.")
else:
    readiness_right.warning("Not ready: two monthly expiries are required.")

if cycle is not None:
    st.subheader("Book V2 Monthly Cycle")
    cycle_left, cycle_mid, cycle_right = st.columns(3)
    cycle_left.metric("Current Monthly Expiry", cycle.current_expiry.isoformat())
    cycle_mid.metric("Next Monthly Expiry", cycle.next_expiry.isoformat())
    cycle_right.metric("Strategy Action", cycle.action.value.upper())
    st.caption(cycle.reason)
else:
    st.info("Monthly cycle status is unavailable.")
    st.caption("Two provider-reported monthly expiries are required.")

left, right = st.columns(2)

with left:
    expiry = st.date_input(
        "Option expiry",
        value=cycle.next_expiry if cycle is not None else india_now.date(),
        key="nifty_v2_trade_expiry",
    )
    strike = st.number_input("CALL strike", min_value=1.0, value=25000.0, step=50.0)

with right:
    observed_date = st.date_input(
        "Observation date", value=india_now.date(), key="nifty_v2_trade_observation_date"
    )
    spot = st.number_input("NIFTY spot", min_value=0.01, value=25000.0, step=1.0)
    ltp = st.number_input("CALL LTP", min_value=0.0, value=500.0, step=0.05)

    observation = LivePaperObservation(
        observed_date=observed_date,
        spot=spot,
        ltp=ltp,
    )

    if st.button("Start Paper Trade", type="primary"):
        try:
            session.start(expiry=expiry, strike=strike, observation=observation)
            st.success("Paper trade started. No broker order was submitted.")
        except ValueError as exc:
            st.error(str(exc))

    if st.button("Close Paper Trade"):
        try:
            closed = session.close(observation)
            st.success(f"Paper trade closed: {closed.points_pnl:.2f} points")
        except ValueError as exc:
            st.error(str(exc))
if st.button("Refresh Live Paper Observation"):
    st.rerun()

if st.button("Preview Automatic CALL"):
    if cycle is None:
        st.warning("Automatic cycle unavailable: two monthly expiries are required.")
    else:
        preview_provider = fetch_option_chain_cached("NIFTY", cycle.next_expiry.isoformat())
        if preview_provider.status != "AVAILABLE" or preview_provider.spot is None:
            st.warning(f"Next-series option chain unavailable: {preview_provider.message}")
        else:
            preview = select_deepest_itm_call(
                preview_provider.chain,
                spot=preview_provider.spot,
                expiry=cycle.next_expiry,
                observed_date=observed_date,
            )
            st.subheader("Automatic CALL Preview")
            preview_left, preview_mid, preview_right = st.columns(3)
            preview_left.metric("Expiry", preview.contract.expiry.isoformat())
            preview_mid.metric("Strike", f"{preview.contract.strike:.0f}")
            preview_right.metric("CALL LTP", f"{preview.observation.ltp:.2f}")
            st.caption(f"NIFTY spot: {preview.observation.spot:.2f}")

automatic_data_ready = (
    provider_data_ready(provider)
    and market_session_ready(datetime.now(UTC))
    and market_data_is_fresh(provider_fetched_at, now=datetime.now(UTC))
)

if not automatic_data_ready:
    st.caption(
        "Automatic Book V2 cycle is blocked when provider data is unavailable "
        "or the regular NSE market session is closed."
    )

if st.button(
    "Run Automatic Book V2 Cycle",
    type="primary",
    disabled=not automatic_data_ready,
):
    try:
        if cycle is None:
            st.warning("Automatic cycle unavailable: two monthly expiries are required.")
        else:
            if auto_strike:
                next_provider = fetch_option_chain("NIFTY", cycle.next_expiry.isoformat())
                if next_provider.status != "AVAILABLE" or next_provider.spot is None:
                    raise ValueError(
                        f"Next-series option chain unavailable: {next_provider.message}"
                    )
                market_observation = select_deepest_itm_call(
                    next_provider.chain,
                    spot=next_provider.spot,
                    expiry=cycle.next_expiry,
                    observed_date=observed_date,
                )
                st.info(
                    f"Auto-selected deepest ITM CALL: {market_observation.contract.strike:.0f} "
                    f"@ LTP {market_observation.observation.ltp:.2f}"
                )
            else:
                market_observation = NiftyV2MarketObservation(
                    contract=NiftyCallContract(
                        expiry=cycle.next_expiry,
                        strike=strike,
                    ),
                    observation=observation,
                )
            result = auto_cycle.process(
                expiries=provider.expiries,
                observed_date=observed_date,
                observation=market_observation,
            )
            if result is None:
                st.warning("Automatic cycle could not be evaluated.")
            else:
                st.success(f"Book V2 action: {result.action.value.upper()} — {result.reason}")
                st.caption(
                    f"Observation: {result.observed_date.isoformat()} | "
                    f"Strike {result.strike:.0f} | Spot {result.spot:.2f} | "
                    f"LTP {result.ltp:.2f}"
                )
                st.session_state.nifty_v2_decision_history.append(
                    {
                        "Observed": result.observed_date,
                        "Current Expiry": result.current_expiry,
                        "Next Expiry": result.next_expiry,
                        "Strike": result.strike,
                        "Spot": result.spot,
                        "LTP": result.ltp,
                        "Action": result.action.value.upper(),
                        "Reason": result.reason,
                    }
                )
                st.session_state.nifty_v2_decision_history = (
                    st.session_state.nifty_v2_decision_history[-100:]
                )
    except ValueError as exc:
        st.error(str(exc))

if st.session_state.nifty_v2_decision_history:
    st.subheader("Automatic Decision History")
    st.dataframe(
        st.session_state.nifty_v2_decision_history,
        use_container_width=True,
    )
    history_csv = StringIO()
    history = st.session_state.nifty_v2_decision_history
    writer = csv.DictWriter(history_csv, fieldnames=history[0].keys())
    writer.writeheader()
    writer.writerows(history)
    st.download_button(
        "Download Decision History CSV",
        data=history_csv.getvalue(),
        file_name="nifty_v2_decision_history.csv",
        mime="text/csv",
    )
    if st.button("Clear Decision History"):
        st.session_state.nifty_v2_decision_history = []
        st.rerun()

manual_entry_ready = observed_date < expiry
if not manual_entry_ready:
    st.warning(
        "Paper entry is blocked because the option expiry must be after the "
        "observation date. Select a future expiry before starting a paper trade."
    )

if st.button("Start Paper Trade", type="secondary", disabled=not manual_entry_ready):
    try:
        session.start(expiry=expiry, strike=strike, observation=observation)
        st.success("Paper trade started. No broker order was submitted.")
    except ValueError as exc:
        st.error(str(exc))

active = session.trader.active_trade
if active is not None:
    st.subheader("Active Paper Trade")
    st.write(
        {
            "expiry": active.contract.expiry.isoformat(),
            "strike": active.contract.strike,
            "entry_date": active.entry_date.isoformat(),
            "entry_ltp": active.entry_ltp,
        }
    )

if session.trader.completed_trades:
    st.subheader("Paper Session Summary")
    total_points = sum(trade.points_pnl or 0.0 for trade in session.trader.completed_trades)
    summary_left, summary_mid, summary_right = st.columns(3)
    summary_left.metric("Completed Trades", len(session.trader.completed_trades))
    summary_mid.metric("Total Points P&L", f"{total_points:.2f}")
    summary_right.metric(
        "Session Status",
        "ACTIVE" if session.trader.active_trade is not None else "FLAT",
    )

    st.subheader("Completed Paper Trades")
    st.dataframe(
        [
            {
                "Expiry": trade.contract.expiry,
                "Strike": trade.contract.strike,
                "Entry": trade.entry_ltp,
                "Exit": trade.exit_ltp,
                "Points P&L": trade.points_pnl,
            }
            for trade in session.trader.completed_trades
        ],
        use_container_width=True,
    )
    report_rows = [
        {
            "Expiry": trade.contract.expiry.isoformat(),
            "Strike": trade.contract.strike,
            "Entry": trade.entry_ltp,
            "Exit": trade.exit_ltp,
            "Points P&L": trade.points_pnl,
        }
        for trade in session.trader.completed_trades
    ]
    report_buffer = StringIO()
    report_writer = csv.DictWriter(report_buffer, fieldnames=report_rows[0].keys())
    report_writer.writeheader()
    report_writer.writerows(report_rows)
    st.download_button(
        "Download Paper Session Report CSV",
        data=report_buffer.getvalue(),
        file_name="nifty_v2_paper_session_report.csv",
        mime="text/csv",
    )
