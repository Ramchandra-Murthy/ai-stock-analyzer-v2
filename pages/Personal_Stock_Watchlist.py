"""Personal stock watchlist page inspired by the supplied reference screenshot."""

from __future__ import annotations

import re
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import yfinance as yf

from scanner.gainers import build_gainer_rows, coverage_message
from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES
from services.parallel_download import download_in_parallel
from services.portfolio_calculations import is_actual_holding, position_valuation
from services.watchlist_service import (
    OWNER_ID,
    WatchlistError,
    add_symbol,
    list_stock_records,
    remove_symbol,
    update_stock_details,
)
from services.watchlist_ui import get_or_create_default_watchlist

EXCHANGES = {"NSE": ".NS", "BSE": ".BO"}
STATUSES = ["Watching", "Bought", "Sold", "Avoid"]
INVESTMENT_TYPES = ["Delivery", "Swing", "Intraday", "Investment", "Options", "Other"]


def _market_session_open() -> bool:
    """Approximate NSE/BSE cash session; exchange holidays are not inferred."""
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    return now.weekday() < 5 and time(9, 15) <= now.time() <= time(15, 30)


@st.cache_data(ttl=45, show_spinner=False)
def _quote_table(records: list[dict[str, Any]], exchange: str) -> pd.DataFrame:
    """Cache watchlist quotes briefly so ordinary widget reruns do not refetch every symbol."""
    from services.market_service import get_latest_available_price

    rows: list[dict[str, Any]] = []
    for record in records:
        symbol = str(record["symbol"]).strip().upper()
        record_exchange = (
            "BSE" if symbol.endswith(".BO") else ("NSE" if symbol.endswith(".NS") else exchange)
        )
        ticker = symbol if symbol.endswith((".NS", ".BO")) else symbol + EXCHANGES[record_exchange]
        quote = get_latest_available_price(ticker, record_exchange)
        last = quote.get("price")
        previous = quote.get("previous_close")
        if last is None:
            rows.append(
                {
                    "Symbol": symbol,
                    "Current price": "Unavailable",
                    "Price trend": "Unknown",
                    "Alert": "Price unavailable — cannot check target or loss",
                    "Change today (₹)": None,
                    "Change today (%)": None,
                    "Volume": None,
                    "Data": "Unavailable",
                }
            )
            continue

        change = float(last) - float(previous) if previous is not None else None
        change_pct = quote.get("change_pct")
        if change is not None and change > 0:
            price_display = f"▲ ₹{float(last):,.2f}"
            trend = "Up"
        elif change is not None and change < 0:
            price_display = f"▼ ₹{float(last):,.2f}"
            trend = "Down"
        else:
            price_display = f"→ ₹{float(last):,.2f}"
            trend = "Flat/unknown"

        target = float(record.get("target_price") or 0)
        stop_loss = float(record.get("stop_loss") or 0)
        entry = float(record.get("entry_price") or 0)
        if target > 0 and float(last) >= target:
            alert = f"🎯 TARGET ACHIEVED — ₹{float(last):,.2f} reached target ₹{target:,.2f}"
        elif stop_loss > 0 and float(last) <= stop_loss:
            alert = f"🚨 STOP-LOSS BREACHED — ₹{float(last):,.2f} is at/below ₹{stop_loss:,.2f}"
        elif entry > 0 and float(last) < entry:
            alert = f"⚠️ LOSING — ₹{float(last):,.2f} is below entry ₹{entry:,.2f}"
        elif trend == "Down":
            alert = "⚠️ PRICE FALLING today"
        else:
            alert = "No target/loss alert"

        rows.append(
            {
                "Symbol": symbol,
                "Current price": price_display,
                "Price trend": trend,
                "Alert": alert,
                "Change today (₹)": round(change, 2) if change is not None else None,
                "Change today (%)": round(float(change_pct), 2) if change_pct is not None else None,
                "Volume": "—",
                "Data": (
                    f"{quote.get('frequency', 'unknown')} via {quote.get('source', 'market provider')}"
                ),
            }
        )
    return pd.DataFrame(rows)


@st.cache_data(ttl=300, show_spinner=False)
def _scan_market_gainers(
    exchange: str, cap_segment: str, limit: int = 10, depth: int = 0
) -> pd.DataFrame:
    """Scan a bounded candidate list. The result carries a coverage note in ``attrs``."""
    candidates = NSE_CANDIDATES if exchange == "NSE" else BSE_CANDIDATES
    suffix = EXCHANGES[exchange]
    # BSE .BO history is less consistently available from Yahoo than NSE .NS, but scanning only
    # 8 of 80 BSE names hid most of the exchange. Chunks now download concurrently, so a larger
    # BSE pool costs roughly one slow chunk instead of the sum of all of them.
    candidate_limit = depth if depth > 0 else (24 if exchange == "BSE" else 15)
    tickers = [f"{symbol}{suffix}" for symbol in candidates[:candidate_limit]]
    if not tickers:
        return pd.DataFrame()

    from services.resilient_market_data import download_symbol_frames

    chunk = 6 if exchange == "BSE" else 10
    intraday_frames, _intraday_missing = download_in_parallel(
        download_symbol_frames,
        tickers,
        chunk_size=chunk,
        workers=4,
        period="1d",
        interval="5m",
        auto_adjust=False,
        batch_size=chunk,
        timeout=4 if exchange == "BSE" else 6,
    )
    daily_frames, _daily_missing = download_in_parallel(
        download_symbol_frames,
        tickers,
        chunk_size=chunk,
        workers=4,
        period="5d",
        interval="1d",
        auto_adjust=False,
        batch_size=chunk,
        timeout=4 if exchange == "BSE" else 8,
    )

    scan = build_gainer_rows(tickers, intraday_frames, daily_frames, suffix)
    rows = scan.rows
    coverage = coverage_message(scan, exchange, len(candidates))
    if not rows:
        empty = pd.DataFrame()
        empty.attrs["coverage"] = coverage
        return empty

    # BSE cap lookups are especially slow; enrich only one BSE mover (three for NSE).
    cap_lookup_limit = 1 if exchange == "BSE" else 3
    for row in rows[:cap_lookup_limit]:
        try:
            market_cap_value = yf.Ticker(row["Ticker"]).fast_info.get("market_cap")
            if market_cap_value:
                # Yahoo market cap is expected in the listing currency; keep labels unverified otherwise.
                market_cap_inr = float(market_cap_value)
                row["Market cap (₹)"] = market_cap_inr
                if market_cap_inr >= 200_000_000_000:
                    row["Cap segment"] = "Large-cap"
                elif market_cap_inr >= 50_000_000_000:
                    row["Cap segment"] = "Mid-cap"
                else:
                    row["Cap segment"] = "Small-cap"
        except Exception:
            continue

    frame = pd.DataFrame(rows)
    if cap_segment != "All":
        frame = frame.loc[frame["Cap segment"] == cap_segment]
    frame = frame.loc[frame["Change (%)"] > 0].head(limit).copy()
    frame.attrs["coverage"] = coverage
    if frame.empty:
        return frame
    frame["Price"] = frame["Price"].map(lambda value: f"₹{value:,.2f}")
    frame["Change (%)"] = frame["Change (%)"].map(lambda value: f"+{value:.2f}%")
    frame["Volume"] = frame["Volume"].map(
        lambda value: (
            "—"
            if pd.isna(value)
            else (
                f"{value / 1_000_000:.1f}M"
                if value >= 1_000_000
                else f"{value / 1_000:.1f}K" if value >= 1_000 else f"{int(value):,}"
            )
        )
    )
    frame["Market cap"] = frame["Market cap (₹)"].map(
        lambda value: (
            "Unverified"
            if pd.isna(value)
            else (
                f"₹{value / 1_000_000_000_000:.2f}T"
                if value >= 1_000_000_000_000
                else f"₹{value / 1_000_000_000:.1f}B"
            )
        )
    )
    result = frame[
        ["Symbol", "Company", "Price", "Change (%)", "Volume", "Cap segment", "Market cap"]
    ].reset_index(drop=True)
    result.attrs["coverage"] = coverage
    return result


def _market_gainers(
    exchange: str, cap_segment: str, limit: int = 10, depth: int = 0
) -> pd.DataFrame:
    """Cached scan that never keeps an empty result.

    A transient provider failure used to be cached for five minutes, leaving the exchange blank
    until the entry expired. An empty scan is cleared so the next click fetches fresh data.
    """
    result = _scan_market_gainers(exchange, cap_segment, limit, depth)
    if result.empty:
        _scan_market_gainers.clear()
    return result


def _risk_metrics(
    entry: float, current: float | None, target: float, stop_loss: float
) -> tuple[float | None, float | None, float | None]:
    """Return current-price distance to target/stop and entry-based reward-to-risk."""
    target_distance = (target - current) / current * 100 if current and target > 0 else None
    stop_distance = (current - stop_loss) / current * 100 if current and stop_loss > 0 else None
    risk = entry - stop_loss if entry > stop_loss > 0 else None
    reward = target - entry if target > entry > 0 else None
    reward_risk = reward / risk if reward is not None and risk else None
    return target_distance, stop_distance, reward_risk


def _render_manual_asset_category(category_name: str, prefix: str) -> None:
    """Track mutual funds, commodities and currencies with transparent manual quotes."""
    try:
        _, watchlist_id, _ = get_or_create_default_watchlist()
        all_records = list_stock_records(OWNER_ID, watchlist_id)
    except WatchlistError as exc:
        st.error(f"Investment storage unavailable: {exc}")
        return
    records = [r for r in all_records if r.get("asset_category") == category_name]
    st.subheader(f"{category_name} portfolio")
    with st.expander("Add investment", expanded=True):
        with st.form(f"add_asset_{prefix}", clear_on_submit=True):
            name = st.text_input("Instrument / fund / currency pair", key=f"{prefix}_name")
            c1, c2, c3 = st.columns(3)
            entry = c1.number_input(
                "Entry price / NAV / rate (₹)", min_value=0.0, value=0.0, key=f"{prefix}_entry"
            )
            current = c2.number_input(
                "Current price / NAV / rate (₹)", min_value=0.0, value=0.0, key=f"{prefix}_current"
            )
            quantity = c3.number_input(
                "Units / quantity", min_value=0.0, value=0.0, key=f"{prefix}_quantity"
            )
            c4, c5, c6 = st.columns(3)
            target = c4.number_input("Target (₹)", min_value=0.0, value=0.0, key=f"{prefix}_target")
            stop = c5.number_input("Stop-loss (₹)", min_value=0.0, value=0.0, key=f"{prefix}_stop")
            bought = c6.date_input("Purchase date", value=date.today(), key=f"{prefix}_date")
            extra: dict[str, Any] = {}
            if prefix == "MF":
                extra["scheme_details"] = st.text_input("Scheme / plan", key="mf_scheme_details")
            elif prefix == "CMD":
                cc1, cc2 = st.columns(2)
                extra["exchange"] = cc1.selectbox(
                    "Exchange", ["MCX", "NCDEX", "Other"], key="cmd_exchange"
                )
                extra["expiry"] = cc2.date_input(
                    "Contract expiry", value=date.today(), key="cmd_expiry"
                ).isoformat()
                extra["contract_size"] = st.text_input(
                    "Contract / lot size", key="cmd_contract_size"
                )
            else:
                cc1, cc2 = st.columns(2)
                extra["currency_pair"] = cc1.text_input("Currency pair", key="fx_pair")
                extra["exchange"] = cc2.selectbox(
                    "Market", ["NSE", "BSE", "Other"], key="fx_exchange"
                )
            notes = st.text_area("Notes", key=f"{prefix}_notes")
            submit = st.form_submit_button("Save investment", use_container_width=True)
        if submit:
            clean_name = name.strip()
            if not clean_name:
                st.error("Enter the instrument name.")
            elif quantity <= 0:
                st.error("Units / quantity must be greater than zero.")
            else:
                slug = re.sub(r"[^A-Z0-9]+", "-", clean_name.upper()).strip("-")[:24]
                symbol = f"{prefix}-{slug}"
                try:
                    added = add_symbol(
                        OWNER_ID,
                        watchlist_id,
                        symbol,
                        {
                            "entry_price": entry or None,
                            "target_price": target or None,
                            "stop_loss": stop or None,
                            "quantity": max(1, int(quantity)),
                            "investment_type": "Investment",
                            "purchase_date": bought.isoformat(),
                            "notes": notes.strip(),
                            "status": "Bought",
                            "asset_category": category_name,
                            "asset_details": {
                                "instrument_name": clean_name,
                                "current_price_manual": current or None,
                                "units_quantity": quantity,
                                **extra,
                            },
                        },
                    )
                    (
                        st.success(f"Saved {clean_name}.")
                        if added
                        else st.warning("That instrument is already saved.")
                    )
                    st.rerun()
                except WatchlistError as exc:
                    st.error(f"Could not save investment: {exc}")
    if not records:
        st.info(f"No {category_name.lower()} saved yet.")
        return
    rows = []
    for record in records:
        details = record.get("asset_details") or {}
        units = float(details.get("units_quantity") or record.get("quantity") or 0)
        entry_price = float(record.get("entry_price") or 0)
        current_price = details.get("current_price_manual")
        current_price = float(current_price) if current_price not in (None, "") else None
        holding = is_actual_holding(record)
        invested = entry_price * units if holding and entry_price > 0 and units > 0 else None
        current_value = (
            current_price * units if holding and current_price is not None and units > 0 else None
        )
        target_distance, stop_distance, reward_risk = _risk_metrics(
            entry_price,
            current_price,
            float(record.get("target_price") or 0),
            float(record.get("stop_loss") or 0),
        )
        rows.append(
            {
                "Instrument": details.get("instrument_name") or record.get("symbol"),
                "Purchase date": record.get("purchase_date") or "—",
                "Units / quantity": units,
                "Entry (₹)": entry_price or None,
                "Current price / NAV / rate (manual)": current_price,
                "Invested (₹)": invested,
                "Current value (₹)": current_value,
                "P/L (₹)": (
                    current_value - invested
                    if current_value is not None and invested is not None
                    else None
                ),
                "Target distance (%)": target_distance,
                "Stop distance (%)": stop_distance,
                "Reward / risk": reward_risk,
                "Target (₹)": record.get("target_price"),
                "Stop-loss (₹)": record.get("stop_loss"),
                "Status": record.get("status"),
                "Notes": record.get("notes") or "—",
                "Contract / scheme details": ", ".join(
                    f"{k}: {v}"
                    for k, v in details.items()
                    if k not in {"instrument_name", "current_price_manual", "units_quantity"}
                ),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption(
        "Current NAV/rate/price is manually entered, not live market data. P/L is an estimate."
    )
    with st.expander("Edit or delete saved investment"):
        selected = st.selectbox(
            "Select instrument", [r["symbol"] for r in records], key=f"{prefix}_selected"
        )
        record = next(r for r in records if r["symbol"] == selected)
        details = record.get("asset_details") or {}
        with st.form(f"{prefix}_edit"):
            edit_entry = st.number_input(
                "Entry price / NAV / rate",
                min_value=0.0,
                value=float(record.get("entry_price") or 0),
                key=f"{prefix}_edit_entry",
            )
            edit_current = st.number_input(
                "Current price / NAV / rate",
                min_value=0.0,
                value=float(details.get("current_price_manual") or 0),
                key=f"{prefix}_edit_current",
            )
            edit_units = st.number_input(
                "Units / quantity",
                min_value=0.0,
                value=float(details.get("units_quantity") or record.get("quantity") or 0),
                key=f"{prefix}_edit_units",
            )
            edit_target = st.number_input(
                "Target",
                min_value=0.0,
                value=float(record.get("target_price") or 0),
                key=f"{prefix}_edit_target",
            )
            edit_stop = st.number_input(
                "Stop-loss",
                min_value=0.0,
                value=float(record.get("stop_loss") or 0),
                key=f"{prefix}_edit_stop",
            )
            edit_status = st.selectbox(
                "Status",
                STATUSES,
                index=(
                    STATUSES.index(record.get("status") or "Watching")
                    if record.get("status") in STATUSES
                    else 0
                ),
                key=f"{prefix}_edit_status",
            )
            edit_notes = st.text_area(
                "Notes", value=str(record.get("notes") or ""), key=f"{prefix}_edit_notes"
            )
            save = st.form_submit_button("Save changes")
        if save:
            try:
                update_stock_details(
                    OWNER_ID,
                    watchlist_id,
                    selected,
                    {
                        "entry_price": edit_entry or None,
                        "target_price": edit_target or None,
                        "stop_loss": edit_stop or None,
                        "quantity": max(1, int(edit_units)),
                        "investment_type": record.get("investment_type") or "Investment",
                        "purchase_date": record.get("purchase_date"),
                        "notes": edit_notes,
                        "status": edit_status,
                        "asset_category": category_name,
                        "asset_details": {
                            **details,
                            "current_price_manual": edit_current or None,
                            "units_quantity": edit_units,
                        },
                    },
                )
                st.success("Investment updated.")
                st.rerun()
            except WatchlistError as exc:
                st.error(f"Could not update investment: {exc}")
        if st.button("Request delete", key=f"{prefix}_delete"):
            st.session_state[f"{prefix}_pending_delete"] = selected
        if st.session_state.get(f"{prefix}_pending_delete") == selected:
            st.warning("Confirm deletion? This cannot be undone.")
            a, b = st.columns(2)
            if a.button("Confirm delete", key=f"{prefix}_confirm"):
                try:
                    remove_symbol(OWNER_ID, watchlist_id, selected)
                    st.session_state.pop(f"{prefix}_pending_delete", None)
                    st.rerun()
                except WatchlistError as exc:
                    st.error(f"Could not delete: {exc}")
            if b.button("Cancel", key=f"{prefix}_cancel"):
                st.session_state.pop(f"{prefix}_pending_delete", None)
                st.rerun()


def show() -> None:
    st.markdown(
        """
        <style>
        .watchlist-header {font-size:2.1rem;font-weight:750;letter-spacing:-.04em;margin-bottom:.1rem}
        .watchlist-subtitle {color:#64748b;margin-bottom:1rem}
        div[data-testid="stDataFrame"] {border:1px solid #e2e8f0;border-radius:8px}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="watchlist-header">Stocks Watchlist</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="watchlist-subtitle">Personal watchlist · saved investment details · market data when available</div>',
        unsafe_allow_html=True,
    )

    try:
        _, summary_watchlist_id, _ = get_or_create_default_watchlist()
        summary_records = list_stock_records(OWNER_ID, summary_watchlist_id)
        category_names = ["Stocks / F&O", "Mutual Funds", "Commodity", "Currency"]
        category_totals = {
            name: {"count": 0, "invested": 0.0, "manual_current": 0.0, "manual_count": 0}
            for name in category_names
        }
        for summary_record in summary_records:
            category_name = summary_record.get("asset_category", "Stocks / F&O")
            if category_name not in category_totals:
                category_name = "Stocks / F&O"
            asset_details = summary_record.get("asset_details") or {}
            qty = float(asset_details.get("units_quantity") or summary_record.get("quantity") or 0)
            if asset_details.get("instrument_type") in {"Futures", "Options"}:
                qty *= int(asset_details.get("lot_size") or 1)
            entry = float(summary_record.get("entry_price") or 0)
            summary = category_totals[category_name]
            summary["count"] += 1
            if is_actual_holding(summary_record):
                summary["invested"] += entry * qty
                manual_price = asset_details.get("current_price_manual")
                if manual_price not in (None, ""):
                    summary["manual_current"] += float(manual_price) * qty
                    summary["manual_count"] += 1
        st.subheader("Portfolio overview — all categories")
        overview = st.columns(4)
        overview[0].metric("Total saved instruments", len(summary_records))
        overview[1].metric(
            "Total invested", f"₹{sum(v['invested'] for v in category_totals.values()):,.2f}"
        )
        overview[2].metric(
            "Manual-value positions", sum(v["manual_count"] for v in category_totals.values())
        )
        overview[3].metric(
            "Categories in use", sum(v["count"] > 0 for v in category_totals.values())
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Category": name,
                        "Saved positions": values["count"],
                        "Invested (₹)": values["invested"],
                        "Current value from manual prices (₹)": (
                            values["manual_current"] if values["manual_count"] else None
                        ),
                        "Manual prices available": values["manual_count"],
                    }
                    for name, values in category_totals.items()
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    except WatchlistError as exc:
        st.warning(f"Portfolio overview unavailable: {exc}")

    category = st.tabs(["Stocks / F&O", "Mutual Funds", "Commodity", "Currency"])
    with category[1]:
        _render_manual_asset_category("Mutual Funds", "MF")
    with category[2]:
        _render_manual_asset_category("Commodity", "CMD")
    with category[3]:
        _render_manual_asset_category("Currency", "FX")

    with category[0]:
        try:
            _, watchlist_id, _ = get_or_create_default_watchlist()
        except WatchlistError as exc:
            st.error("Personal watchlist storage is unavailable.")
            st.warning(str(exc))
            st.info(
                "Check the SUPABASE_URL in Streamlit Secrets and confirm that the "
                "project URL is copied exactly from the Supabase dashboard. "
                "The rest of the app should remain available."
            )
            return

        selected_type = st.radio(
            "Instrument",
            ["Stock", "Futures", "Options"],
            horizontal=True,
            key="personal_watchlist_instrument",
        )
        with st.expander("ADD", expanded=True):
            # Keep the symbol input outside the form so Streamlit updates its
            # session state immediately while the user types. Form widgets do not
            # trigger a rerun until submit, which caused empty/stale symbols on
            # some client sessions.
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.text_input(
                "Stock symbol",
                placeholder="e.g. RELIANCE",
                key="personal_watchlist_add_symbol",
            )
            with st.form("personal_watchlist_add", clear_on_submit=False):
                exchange = col2.selectbox("Exchange", ["NSE", "BSE"])
                investment_type = col3.selectbox("Type", INVESTMENT_TYPES)
                col4, col5, col6 = st.columns(3)
                entry_price = col4.number_input(
                    "Entry price (₹)", min_value=0.0, value=0.0, step=1.0
                )
                target_price = col5.number_input("Target (₹)", min_value=0.0, value=0.0, step=1.0)
                stop_loss = col6.number_input("Stop-loss (₹)", min_value=0.0, value=0.0, step=1.0)
                col7, col8 = st.columns(2)
                quantity = col7.number_input("Quantity", min_value=0, value=0, step=1)
                purchase_date = col8.date_input("Purchase date", value=date.today())
                contract_details: dict[str, Any] = {"instrument_type": selected_type}
                if selected_type in {"Futures", "Options"}:
                    contract_col1, contract_col2 = st.columns(2)
                    contract_details["expiry_date"] = contract_col1.date_input(
                        "Contract expiry", value=date.today(), key="fno_expiry"
                    ).isoformat()
                    contract_details["lot_size"] = contract_col2.number_input(
                        "Lot size", min_value=1, value=1, step=1, key="fno_lot_size"
                    )
                    if selected_type == "Options":
                        contract_col3, contract_col4 = st.columns(2)
                        contract_details["strike_price"] = contract_col3.number_input(
                            "Strike price", min_value=0.0, value=0.0, key="fno_strike"
                        )
                        contract_details["option_type"] = contract_col4.selectbox(
                            "Option type", ["CE", "PE"], key="fno_option_type"
                        )
                    contract_details["current_price_manual"] = st.number_input(
                        "Contract premium / price (manual ₹)",
                        min_value=0.0,
                        value=0.0,
                        key="fno_current_price",
                    )
                notes = st.text_input("Notes")
                submitted = st.form_submit_button("＋ Add to watchlist", use_container_width=True)

            if submitted:
                submitted_symbol = st.session_state.get("personal_watchlist_add_symbol", "")
                normalized = str(submitted_symbol or "").strip().upper()
                if not normalized:
                    st.error(
                        "Enter a stock symbol in the Stock symbol field, then "
                        "click ＋ Add to watchlist."
                    )
                else:
                    if not normalized.endswith((".NS", ".BO")):
                        normalized += EXCHANGES[exchange]
                    if selected_type in {"Futures", "Options"}:
                        expiry_key = str(contract_details.get("expiry_date", "")).replace("-", "")
                        underlying = normalized.removesuffix(".NS").removesuffix(".BO")
                        if selected_type == "Futures":
                            normalized = f"F-{underlying[:12]}-{expiry_key}"
                        else:
                            strike = float(contract_details.get("strike_price") or 0)
                            if strike <= 0:
                                st.error("Enter a valid strike price for an option contract.")
                                st.stop()
                            normalized = f"O-{underlying[:10]}-{expiry_key}-{int(strike)}-{contract_details.get('option_type', 'CE')}"
                    details = {
                        "investment_type": investment_type,
                        "entry_price": entry_price or None,
                        "target_price": target_price or None,
                        "stop_loss": stop_loss or None,
                        "quantity": quantity or None,
                        "purchase_date": purchase_date.isoformat(),
                        "notes": notes.strip(),
                        "status": "Watching",
                        "asset_category": "Stocks / F&O",
                        "asset_details": contract_details,
                    }
                    try:
                        added = add_symbol(OWNER_ID, watchlist_id, normalized, details)
                        if added:
                            st.success(f"Added {normalized}.")
                        else:
                            st.warning(f"{normalized} is already in this watchlist.")
                        st.rerun()
                    except WatchlistError as exc:
                        st.error(str(exc))

        try:
            records = [
                record
                for record in list_stock_records(OWNER_ID, watchlist_id)
                if record.get("asset_category", "Stocks / F&O") == "Stocks / F&O"
            ]
        except WatchlistError as exc:
            st.error(f"Could not load saved watchlist: {exc}")
            return

        # Keep market-data requests out of ordinary Streamlit reruns.
        # Quotes are fetched only after the user explicitly asks for them.
        quoteable_records = [
            record
            for record in records
            if (record.get("asset_details") or {}).get("instrument_type")
            not in {"Futures", "Options"}
        ]
        quote_signature = tuple(
            sorted(str(record.get("symbol", "")) for record in quoteable_records)
        )
        quote_frame_key = "personal_watchlist_quote_frame"
        quote_signature_key = "personal_watchlist_quote_signature"
        if st.session_state.get(quote_signature_key) != quote_signature:
            st.session_state.pop(quote_frame_key, None)
            st.session_state[quote_signature_key] = quote_signature

        with st.expander("Market prices (optional — load only when needed)", expanded=False):
            st.caption(
                "Loading prices can take time when the provider is slow. Your saved diary and "
                "edit/remove controls remain available without loading market data."
            )
            if st.button("Load / refresh market prices", key="load_watchlist_market_prices"):
                with st.spinner("Loading market prices…"):
                    try:
                        _quote_table.clear()
                        loaded_quotes = (
                            _quote_table(quoteable_records, "NSE")
                            if quoteable_records
                            else pd.DataFrame()
                        )
                        st.session_state[quote_frame_key] = loaded_quotes
                        st.session_state["personal_watchlist_quotes_checked_at"] = datetime.now(
                            ZoneInfo("Asia/Kolkata")
                        ).strftime("%H:%M:%S IST")
                        st.success("Market-price check completed.")
                    except Exception as exc:
                        st.warning(f"Could not load market prices: {exc}")

        saved_quote_frame = st.session_state.get(quote_frame_key)
        quote_frame = (
            saved_quote_frame.copy()
            if isinstance(saved_quote_frame, pd.DataFrame)
            and st.session_state.get(quote_signature_key) == quote_signature
            else pd.DataFrame()
        )
        quote_by_symbol = (
            {str(row["Symbol"]): row for _, row in quote_frame.iterrows()}
            if not quote_frame.empty and "Symbol" in quote_frame
            else {}
        )

        def numeric_quote(value: Any) -> float | None:
            if value is None or pd.isna(value):
                return None
            match = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?", str(value))
            if not match:
                return None
            try:
                return float(match.group(0).replace(",", ""))
            except ValueError:
                return None

        diary_rows = []
        invested_total = 0.0
        current_value_total = 0.0
        known_value_positions = 0
        holding_positions = 0
        unrealized_pnl_total = 0.0
        for item in records:
            symbol = str(item.get("symbol", "—"))
            entry_value = float(item.get("entry_price") or 0)
            quantity_value = int(item.get("quantity") or 0)
            asset_details = item.get("asset_details") or {}
            lot_size = (
                int(asset_details.get("lot_size") or 1)
                if asset_details.get("instrument_type") in {"Futures", "Options"}
                else 1
            )
            effective_quantity = quantity_value * lot_size
            quote = quote_by_symbol.get(symbol, {})
            current_price = numeric_quote(quote.get("Current price"))
            if current_price is None and asset_details.get("instrument_type") in {
                "Futures",
                "Options",
            }:
                manual_price = asset_details.get("current_price_manual")
                current_price = float(manual_price) if manual_price not in (None, "") else None
            valuation = position_valuation(item, current_price)
            invested = valuation["invested"]
            current_value = valuation["current_value"]
            pnl = valuation["pnl"]
            pnl_pct = valuation["pnl_pct"]
            if valuation["is_holding"]:
                holding_positions += 1
                invested_total += float(invested or 0.0)
                if current_value is not None:
                    current_value_total += float(current_value)
                    known_value_positions += 1
                if pnl is not None:
                    unrealized_pnl_total += float(pnl)
            target_distance, stop_distance, reward_risk = _risk_metrics(
                entry_value,
                current_price,
                float(item.get("target_price") or 0),
                float(item.get("stop_loss") or 0),
            )
            diary_rows.append(
                {
                    "Symbol": symbol,
                    "Instrument": asset_details.get("instrument_type", "Stock"),
                    "Contract expiry": asset_details.get("expiry_date", "—"),
                    "Strike price": asset_details.get("strike_price", "—"),
                    "Option type": asset_details.get("option_type", "—"),
                    "Lot size": asset_details.get("lot_size", "—"),
                    "Investment type": item.get("investment_type") or "Other",
                    "Status": item.get("status") or "Watching",
                    "Purchase date": str(item.get("purchase_date") or "—"),
                    "Quantity / lots": quantity_value,
                    "Effective lot size": lot_size,
                    "Effective units": effective_quantity,
                    "Entry (₹)": entry_value if entry_value else None,
                    "Current price": (
                        f"₹{current_price:,.2f}" if current_price is not None else "Unavailable"
                    ),
                    "Target (₹)": float(item.get("target_price") or 0) or None,
                    "Stop-loss (₹)": float(item.get("stop_loss") or 0) or None,
                    "Invested (₹)": invested,
                    "Current value (₹)": current_value,
                    "P/L (₹)": pnl,
                    "P/L (%)": pnl_pct,
                    "Target distance (%)": target_distance,
                    "Stop distance (%)": stop_distance,
                    "Reward / risk": reward_risk,
                    "Price data": (
                        "Manual contract price"
                        if asset_details.get("instrument_type") in {"Futures", "Options"}
                        else quote.get("Data", "Unavailable")
                    ),
                    "Alert": (
                        "Price unavailable — cannot check target or loss"
                        if current_price is None
                        else (
                            "🎯 TARGET ACHIEVED"
                            if float(item.get("target_price") or 0) > 0
                            and current_price >= float(item.get("target_price") or 0)
                            else (
                                "🚨 STOP-LOSS BREACHED"
                                if float(item.get("stop_loss") or 0) > 0
                                and current_price <= float(item.get("stop_loss") or 0)
                                else quote.get(
                                    "Alert", "Manual contract price; verify before acting"
                                )
                            )
                        )
                    ),
                    "Notes": item.get("notes") or "—",
                }
            )

        st.subheader("Portfolio summary")
        summary_cols = st.columns(4)
        summary_cols[0].metric("Saved instruments", len(records))
        summary_cols[1].metric("Invested amount (Bought only)", f"₹{invested_total:,.2f}")
        summary_cols[2].metric(
            "Current value (Bought only)",
            f"₹{current_value_total:,.2f}" if known_value_positions else "Unavailable",
            help=(
                f"Quotes available for {known_value_positions} of {holding_positions} bought "
                "positions. Watching records are excluded."
            ),
        )
        summary_cols[3].metric(
            "Unrealized P/L (Bought only)",
            f"₹{unrealized_pnl_total:,.2f}" if known_value_positions else "Unavailable",
            help=(
                "Includes only records with status Bought, positive entry price and quantity, "
                "and an available quote. Watching/Sold/Avoid and incomplete records are excluded."
            ),
        )
        st.caption(
            "Only complete records marked Bought count as holdings. Watching records remain "
            "available for price/target alerts but are excluded from invested value and P/L."
        )
        target_cols = st.columns(3)
        target_cols[0].metric(
            "Targets set", sum(float(item.get("target_price") or 0) > 0 for item in records)
        )
        target_cols[1].metric(
            "Stop-losses set", sum(float(item.get("stop_loss") or 0) > 0 for item in records)
        )
        target_cols[2].metric(
            "Bought positions with unavailable quotes", holding_positions - known_value_positions
        )

        st.subheader("Saved investment diary — full details")
        st.caption(
            "Current values and P/L are estimates from available Yahoo Finance observations, "
            "which may be delayed. Unavailable quotes are never treated as zero."
        )
        st.dataframe(pd.DataFrame(diary_rows), use_container_width=True, hide_index=True)

        filter_mode = st.radio("Filter", ["All", "Gainers", "Losers"], horizontal=True)

        with st.expander("📈 Intraday Market Gainers — large, mid and small caps", expanded=True):
            st.caption(
                "Screens a bounded list of NSE/BSE candidates. Market-cap labels are shown only when "
                "the data provider supplies a value; quotes may be delayed and are not exchange-certified."
            )
            gain_cols = st.columns([1, 1, 1, 1])
            gain_exchange = gain_cols[0].selectbox(
                "Exchange", ["NSE", "BSE"], key="gainers_exchange"
            )
            gain_segment = gain_cols[1].selectbox(
                "Market cap",
                ["All", "Large-cap", "Mid-cap", "Small-cap", "Unverified"],
                key="gainers_cap_segment",
            )
            gain_count = gain_cols[2].selectbox("Show", [10, 20, 30], index=0, key="gainers_count")
            gain_depth = gain_cols[3].selectbox(
                "Candidates to scan",
                [24, 48, 80],
                index=0,
                key="gainers_depth",
                help="How many of the curated symbols to check. More is slower but covers more "
                "of the exchange; symbols without data are listed after the scan.",
            )
            if st.button("Scan market gainers", key="scan_market_gainers", type="primary"):
                with st.spinner("Scanning available market data…"):
                    st.session_state["personal_market_gainers_result"] = _market_gainers(
                        gain_exchange, gain_segment, int(gain_count), int(gain_depth)
                    )
                    st.session_state["personal_market_gainers_exchange"] = gain_exchange
            gainers = st.session_state.get("personal_market_gainers_result")
            if isinstance(gainers, pd.DataFrame):
                if gainers.empty:
                    scanned_exchange = st.session_state.get(
                        "personal_market_gainers_exchange", gain_exchange
                    )
                    coverage = gainers.attrs.get("coverage")
                    if coverage:
                        st.info(coverage)
                    st.warning(
                        f"No verified positive movers were returned for {scanned_exchange}. "
                        "This does not mean the market had no gainers: Yahoo Finance may have "
                        "returned insufficient history for the candidate symbols, or the selected "
                        "market-cap filter may have excluded unverified results."
                    )
                    if gain_segment != "All":
                        st.info(
                            "Set Market cap to All and scan again to include symbols whose market "
                            "capitalization could not be verified."
                        )
                    st.caption(
                        "Only provider-backed prices are displayed. Missing or stale data is not "
                        "replaced with estimated prices. NSE/BSE exchange selection is applied to "
                        "the candidate universe; a result is not guaranteed when provider data is absent."
                    )
                else:
                    if gainers.attrs.get("coverage"):
                        st.caption(gainers.attrs["coverage"])
                    st.dataframe(gainers, use_container_width=True, hide_index=True)
                    choices = gainers["Symbol"].astype(str).tolist()
                    selected_gainer = st.selectbox(
                        "Choose a gainer to add", choices, key="personal_gainer_to_add"
                    )
                    add_col, entry_col, target_col, stop_col = st.columns(4)
                    add_entry = entry_col.number_input(
                        "Entry (₹)", min_value=0.0, value=0.0, step=1.0, key="gainer_entry"
                    )
                    add_target = target_col.number_input(
                        "Target (₹)", min_value=0.0, value=0.0, step=1.0, key="gainer_target"
                    )
                    add_stop = stop_col.number_input(
                        "Stop-loss (₹)", min_value=0.0, value=0.0, step=1.0, key="gainer_stop"
                    )
                    if add_col.button("＋ Add to my watchlist", key="add_selected_gainer"):
                        suffix = EXCHANGES.get(
                            st.session_state.get("personal_market_gainers_exchange", "NSE"), ".NS"
                        )
                        selected_ticker = selected_gainer + suffix
                        existing_symbols = {str(item.get("symbol", "")).upper() for item in records}
                        if selected_ticker.upper() in existing_symbols:
                            st.info(f"{selected_ticker} is already in your watchlist.")
                        else:
                            try:
                                add_symbol(
                                    OWNER_ID,
                                    watchlist_id,
                                    selected_ticker,
                                    {
                                        "investment_type": "Intraday",
                                        "entry_price": add_entry or None,
                                        "target_price": add_target or None,
                                        "stop_loss": add_stop or None,
                                        "status": "Watching",
                                        "notes": "Added from Intraday Market Gainers panel",
                                    },
                                )
                                st.success(f"Added {selected_ticker} to your watchlist.")
                                st.rerun()
                            except WatchlistError as exc:
                                st.error(f"Could not add {selected_ticker}: {exc}")

        # Keep deletion controls above the live quote panel so a slow market-data
        # request never hides the basic watchlist management action.
        if records:
            with st.expander("🗑️ Remove a stock", expanded=False):
                quick_remove_symbol = st.selectbox(
                    "Choose stock to remove",
                    [str(item["symbol"]) for item in records],
                    key="quick_remove_symbol",
                )
                st.caption(
                    "This removes the selected symbol and its saved investment diary "
                    "from the personal watchlist."
                )
                if st.button(
                    "Remove selected stock",
                    key="quick_remove_stock",
                    type="secondary",
                ):
                    st.session_state["personal_watchlist_quick_delete_pending"] = (
                        quick_remove_symbol
                    )
                pending_quick_delete = st.session_state.get(
                    "personal_watchlist_quick_delete_pending"
                )
                if pending_quick_delete in {str(item["symbol"]) for item in records}:
                    st.warning(
                        f"Delete {pending_quick_delete} and its saved details? "
                        "This cannot be undone."
                    )
                    quick_yes, quick_no = st.columns(2)
                    if quick_yes.button(
                        "Yes, delete stock",
                        key="quick_confirm_delete_stock",
                        type="primary",
                    ):
                        try:
                            removed = remove_symbol(OWNER_ID, watchlist_id, pending_quick_delete)
                            st.session_state.pop("personal_watchlist_quick_delete_pending", None)
                            if removed:
                                st.success(f"Removed {pending_quick_delete}.")
                                st.rerun()
                            else:
                                st.warning("Stock was not found; nothing was deleted.")
                        except WatchlistError as exc:
                            st.error(f"Could not remove {pending_quick_delete}: {exc}")
                    if quick_no.button(
                        "Cancel — keep stock",
                        key="quick_cancel_delete_stock",
                    ):
                        st.session_state.pop("personal_watchlist_quick_delete_pending", None)
                        st.rerun()

        if not records:
            st.info("Your watchlist is empty. Add your first stock above.")
        else:
            st.caption(
                "Market prices are loaded on demand, not automatically. Provider data may be "
                "delayed or unavailable; verify prices independently before trading."
            )
            if quote_frame.empty:
                st.info("Market prices have not been loaded for this watchlist in this session.")
            else:
                visible_quotes = quote_frame.copy()
                if filter_mode == "Gainers" and "Change today (%)" in visible_quotes:
                    visible_quotes = visible_quotes.loc[visible_quotes["Change today (%)"] > 0]
                elif filter_mode == "Losers" and "Change today (%)" in visible_quotes:
                    visible_quotes = visible_quotes.loc[visible_quotes["Change today (%)"] < 0]
                st.dataframe(visible_quotes, use_container_width=True, hide_index=True)
                checked_at = st.session_state.get("personal_watchlist_quotes_checked_at")
                if checked_at:
                    st.caption(f"Last quote check: {checked_at}")

            with st.expander("Investment diary — edit saved details"):
                symbols = [str(record["symbol"]) for record in records]
                selected = st.selectbox("Select stock", symbols)
                record = next(item for item in records if item["symbol"] == selected)
                with st.form("personal_watchlist_edit"):
                    cols = st.columns(3)
                    entry = cols[0].number_input(
                        "Entry price (₹)",
                        min_value=0.0,
                        value=float(record.get("entry_price") or 0.0),
                        key=f"edit_entry_{selected}",
                    )
                    target = cols[1].number_input(
                        "Target (₹)",
                        min_value=0.0,
                        value=float(record.get("target_price") or 0.0),
                        key=f"edit_target_{selected}",
                    )
                    stop = cols[2].number_input(
                        "Stop-loss (₹)",
                        min_value=0.0,
                        value=float(record.get("stop_loss") or 0.0),
                        key=f"edit_stop_{selected}",
                    )
                    purchase_date_value = (
                        date.fromisoformat(str(record["purchase_date"])[:10])
                        if record.get("purchase_date")
                        else date.today()
                    )
                    edited_purchase_date = st.date_input(
                        "Purchase date",
                        value=purchase_date_value,
                        key=f"edit_purchase_date_{selected}",
                    )
                    cols2 = st.columns(3)
                    qty = cols2[0].number_input(
                        "Quantity",
                        min_value=0,
                        value=int(record.get("quantity") or 0),
                        step=1,
                        key=f"edit_qty_{selected}",
                    )
                    kind = cols2[1].selectbox(
                        "Investment type",
                        INVESTMENT_TYPES,
                        index=(
                            INVESTMENT_TYPES.index(record.get("investment_type") or "Other")
                            if record.get("investment_type") in INVESTMENT_TYPES
                            else INVESTMENT_TYPES.index("Other")
                        ),
                        key=f"edit_type_{selected}",
                    )
                    status = cols2[2].selectbox(
                        "Status",
                        STATUSES,
                        index=(
                            STATUSES.index(record.get("status") or "Watching")
                            if record.get("status") in STATUSES
                            else 0
                        ),
                        key=f"edit_status_{selected}",
                    )
                    note = st.text_area(
                        "Notes", value=str(record.get("notes") or ""), key="edit_notes"
                    )
                    save = st.form_submit_button("Save investment details")
                    if save:
                        try:
                            update_stock_details(
                                OWNER_ID,
                                watchlist_id,
                                selected,
                                {
                                    "entry_price": entry or None,
                                    "target_price": target or None,
                                    "stop_loss": stop or None,
                                    "quantity": qty or None,
                                    "investment_type": kind,
                                    "purchase_date": edited_purchase_date.isoformat(),
                                    "notes": note,
                                    "status": status,
                                },
                            )
                            st.success("Investment details saved.")
                            st.rerun()
                        except WatchlistError as exc:
                            st.error(str(exc))

                pending_delete_key = "personal_watchlist_pending_delete"
                if st.button(
                    "Remove selected stock",
                    type="secondary",
                    key=f"remove_stock_{selected}",
                ):
                    # Set the pending target and render the confirmation immediately
                    # in this run; do not rerun before the prompt becomes visible.
                    st.session_state[pending_delete_key] = selected

                if st.session_state.get(pending_delete_key) == selected:
                    st.warning(
                        f"Are you sure you want to delete {selected} from your watchlist? "
                        "This cannot be undone."
                    )
                    confirm_col, cancel_col = st.columns(2)
                    with confirm_col:
                        if st.button(
                            f"Yes, delete {selected}",
                            type="primary",
                            key=f"confirm_delete_{selected}",
                        ):
                            try:
                                removed = remove_symbol(OWNER_ID, watchlist_id, selected)
                                st.session_state.pop(pending_delete_key, None)
                                if removed:
                                    st.success(f"Removed {selected}.")
                                    st.rerun()
                                else:
                                    st.warning("Stock was not found.")
                            except WatchlistError as exc:
                                st.error(f"Could not remove {selected}: {exc}")
                    with cancel_col:
                        if st.button("No, keep stock", key=f"cancel_delete_{selected}"):
                            st.session_state.pop(pending_delete_key, None)
                            st.rerun()


show()
