import pandas as pd
import streamlit as st

from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES
from services.market_service import (
    WATCHLIST,
    get_company_name,
    get_latest_available_price,
    get_market_indices,
    scan_market_universe,
)
from services.watchlist_service import (
    WatchlistError,
    add_symbol,
    list_stock_records,
    remove_symbol,
    update_stock_details,
)
from services.watchlist_ui import get_or_create_default_watchlist

SECTOR_STOCKS = {
    "Financials": ["HDFCBANK", "ICICIBANK", "SBIN"],
    "Information Technology": ["TCS", "INFY"],
    "Energy": ["RELIANCE"],
    "Industrials": ["LT"],
    "Consumer Staples": ["ITC", "HINDUNILVR"],
    "Telecommunications": ["BHARTIARTL"],
}

NSE_UNIVERSE = NSE_CANDIDATES
BSE_UNIVERSE = BSE_CANDIDATES
DEFAULT_WATCHLIST = [f"{symbol}.NS" for symbol in WATCHLIST]


def metric_card(title, value, change):
    if value is None:
        st.metric(title, "N/A", "-")
        return
    delta = f"{change:+.2f}%" if isinstance(change, (int, float)) else None
    st.metric(title, value, delta)


def normalize_symbol(symbol, exchange):
    normalized = symbol.strip().upper()
    if not normalized:
        return normalized
    if normalized.endswith((".NS", ".BO")):
        return normalized
    suffix = ".BO" if exchange == "BSE" else ".NS"
    return f"{normalized}{suffix}"


def get_sector_performance():
    rows = []
    for sector, symbols in SECTOR_STOCKS.items():
        changes = []
        for symbol in symbols:
            change = get_latest_available_price(symbol).get("change_pct")
            if isinstance(change, (int, float)):
                changes.append(change)
        average = round(sum(changes) / len(changes), 2) if changes else None
        rows.append(
            {
                "Sector": sector,
                "Average Change %": average,
                "Stocks Available": len(changes),
            }
        )
    return (
        pd.DataFrame(rows)
        .sort_values("Average Change %", ascending=False, na_position="last")
        .reset_index(drop=True)
    )


def get_personal_watchlist(symbols):
    rows = []
    for symbol in symbols:
        quote = get_latest_available_price(symbol)
        rows.append(
            {
                "Symbol": symbol,
                "Name": get_company_name(quote.get("symbol", symbol)),
                "Exchange": quote.get("exchange"),
                "Price": quote.get("price"),
                "Change %": quote.get("change_pct"),
                "Observed": quote.get("observed_at"),
                "Frequency": quote.get("frequency"),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "Symbol",
            "Name",
            "Exchange",
            "Price",
            "Change %",
            "Observed",
            "Frequency",
        ],
    )


def scanner_universe(exchange):
    if exchange == "NSE":
        return {"NSE": NSE_UNIVERSE}
    return {"BSE": BSE_UNIVERSE}


# Every widget click reruns this script. These provider calls download one symbol at a
# time (with retries and backoff), so without a cache a single click could re-download the
# whole universe. A short TTL keeps the data current while keeping the page responsive.
MARKET_CACHE_TTL_SECONDS = 120


@st.cache_data(ttl=MARKET_CACHE_TTL_SECONDS, show_spinner=False)
def _cached_market_indices():
    return get_market_indices()


@st.cache_data(ttl=MARKET_CACHE_TTL_SECONDS, show_spinner="Scanning market universe...")
def _cached_universe_scan(exchange):
    return scan_market_universe(scanner_universe(exchange), top_n=10)


@st.cache_data(ttl=MARKET_CACHE_TTL_SECONDS, show_spinner="Loading sector performance...")
def _cached_sector_performance():
    return get_sector_performance()


def show():
    st.title("📈 Indian Market Dashboard")
    if st.button("🔄 Refresh market data"):
        st.cache_data.clear()
    market = _cached_market_indices()
    st.caption(
        "Prices are the latest available Yahoo Finance observations. "
        "Intraday data is provider-sourced 1-minute data, not exchange-tick live data; "
        "percentage change is measured against the prior daily close."
    )

    st.subheader("Market Overview")
    overview = [
        ("NIFTY 50", "NIFTY 50"),
        ("SENSEX", "SENSEX"),
        ("BANK NIFTY", "BANK NIFTY"),
        ("INDIA VIX", "INDIA VIX"),
        ("USD / INR", "USD/INR"),
        ("GOLD", "GOLD"),
    ]
    columns = st.columns(3)
    for index, (label, key) in enumerate(overview):
        with columns[index % 3]:
            metric_card(label, market[key]["value"], market[key]["change"])

    st.divider()
    st.subheader("Exchange")
    selected_exchange = st.radio(
        "Select exchange",
        ["NSE", "BSE"],
        horizontal=True,
        index=0,
    )

    scanner = _cached_universe_scan(selected_exchange)
    if scanner.empty:
        gainers = pd.DataFrame()
        losers = pd.DataFrame()
    else:
        gainers = scanner[scanner["Change %"] >= 0].sort_values("Change %", ascending=False).head(5)
        losers = scanner[scanner["Change %"] < 0].sort_values("Change %", ascending=True).head(5)

    display_columns = ["Symbol", "Name", "Exchange", "Price", "Change %"]
    gainers = gainers[[c for c in display_columns if c in gainers.columns]]
    losers = losers[[c for c in display_columns if c in losers.columns]]

    left, right = st.columns(2)
    with left:
        st.subheader("📈 Top Gainers")
        st.dataframe(gainers, hide_index=True, use_container_width=True)
    with right:
        st.subheader("📉 Top Losers")
        st.dataframe(losers, hide_index=True, use_container_width=True)
    st.caption(
        f"Scanner universe: {selected_exchange}. "
        f"Results are cached for {MARKET_CACHE_TTL_SECONDS} seconds; use Refresh for new data."
    )

    st.divider()
    st.subheader("🔥 Sector Performance")
    st.caption(
        "Average percentage change of the mapped dashboard stocks in each sector. "
        "This is not official NSE sector-index performance."
    )
    st.dataframe(_cached_sector_performance(), hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("⭐ My Personal Watchlist")
    st.caption(
        "No sign-in required. Your saved stock details are stored in the app database. "
        "Anyone with access to this open app can view or change this list."
    )
    user_id, watchlist_id, saved_symbols = get_or_create_default_watchlist(
        None, DEFAULT_WATCHLIST.copy()
    )

    with st.form("add_personal_watchlist_symbol"):
        placeholder = (
            "e.g. TATAMOTORS or TATAMOTORS.NS"
            if selected_exchange == "NSE"
            else "e.g. 500570 or 500570.BO"
        )
        symbol_input = st.text_input(f"Add a {selected_exchange} symbol", placeholder=placeholder)
        detail_col1, detail_col2, detail_col3 = st.columns(3)
        with detail_col1:
            entry_price = st.number_input(
                "Entry price (₹; 0 = unset)", min_value=0.0, value=0.0, step=1.0
            )
            stop_loss = st.number_input(
                "Stop-loss (₹; 0 = unset)", min_value=0.0, value=0.0, step=1.0
            )
        with detail_col2:
            target_price = st.number_input(
                "Target price (₹; 0 = unset)", min_value=0.0, value=0.0, step=1.0
            )
            quantity = st.number_input("Quantity (0 = unset)", min_value=0, value=0, step=1)
        with detail_col3:
            investment_type = st.selectbox(
                "Investment type",
                ["Other", "Delivery", "Swing", "Intraday", "Investment", "Options"],
            )
            status = st.selectbox("Status", ["Watching", "Bought", "Sold", "Avoid"])
        purchase_date = st.date_input("Purchase / planned entry date", value=None)
        notes = st.text_area("Investment notes / rationale")
        submitted = st.form_submit_button("Save stock to watchlist")

    if submitted:
        symbol = normalize_symbol(symbol_input, selected_exchange)
        if not symbol:
            st.warning("Enter a stock symbol first.")
        else:
            details = {
                "entry_price": entry_price or None,
                "stop_loss": stop_loss or None,
                "target_price": target_price or None,
                "quantity": quantity or None,
                "investment_type": investment_type,
                "purchase_date": purchase_date.isoformat() if purchase_date else None,
                "notes": notes.strip(),
                "status": status,
            }
            try:
                if add_symbol(user_id, watchlist_id, symbol, details):
                    st.success(f"Saved {symbol} and its investment details.")
                else:
                    st.info(f"{symbol} is already saved. Select it below to update its details.")
            except (WatchlistError, ValueError) as exc:
                st.warning(str(exc))
            st.rerun()

    records = list_stock_records(user_id, watchlist_id)
    if not records:
        st.info("Your watchlist is empty. Add a symbol above.")
        return

    live = get_personal_watchlist([record["symbol"] for record in records])
    saved = pd.DataFrame(records)
    saved = saved.rename(columns={"symbol": "Symbol"})
    combined = saved.merge(live, on="Symbol", how="left", suffixes=("_saved", "_market"))
    display_columns = [
        "Symbol",
        "Name",
        "Exchange",
        "Price",
        "Change %",
        "entry_price",
        "stop_loss",
        "target_price",
        "quantity",
        "investment_type",
        "purchase_date",
        "status",
        "notes",
        "Observed",
    ]
    st.dataframe(
        combined[[column for column in display_columns if column in combined.columns]],
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("Edit saved stock details")
    record_by_symbol = {record["symbol"]: record for record in records}
    selected_symbol = st.selectbox("Stock to edit", options=list(record_by_symbol))
    selected_record = record_by_symbol[selected_symbol]
    with st.form("edit_personal_watchlist_details"):
        edit_col1, edit_col2, edit_col3 = st.columns(3)
        with edit_col1:
            edit_entry = st.number_input(
                "Entry price (₹; 0 = unset)",
                min_value=0.0,
                value=float(selected_record["entry_price"] or 0.0),
                step=1.0,
                key="edit_entry_price",
            )
            edit_stop = st.number_input(
                "Stop-loss (₹; 0 = unset)",
                min_value=0.0,
                value=float(selected_record["stop_loss"] or 0.0),
                step=1.0,
                key="edit_stop_loss",
            )
        with edit_col2:
            edit_target = st.number_input(
                "Target price (₹; 0 = unset)",
                min_value=0.0,
                value=float(selected_record["target_price"] or 0.0),
                step=1.0,
                key="edit_target_price",
            )
            edit_quantity = st.number_input(
                "Quantity (0 = unset)",
                min_value=0,
                value=int(selected_record["quantity"] or 0),
                step=1,
                key="edit_quantity",
            )
        with edit_col3:
            types = ["Other", "Delivery", "Swing", "Intraday", "Investment", "Options"]
            edit_type = st.selectbox(
                "Investment type",
                types,
                index=(
                    types.index(selected_record["investment_type"])
                    if selected_record["investment_type"] in types
                    else 0
                ),
                key="edit_investment_type",
            )
            statuses = ["Watching", "Bought", "Sold", "Avoid"]
            edit_status = st.selectbox(
                "Status",
                statuses,
                index=(
                    statuses.index(selected_record["status"])
                    if selected_record["status"] in statuses
                    else 0
                ),
                key="edit_status",
            )
        existing_date = selected_record["purchase_date"]
        parsed_date = pd.to_datetime(existing_date).date() if existing_date else None
        edit_date = st.date_input(
            "Purchase / planned entry date", value=parsed_date, key="edit_purchase_date"
        )
        edit_notes = st.text_area(
            "Investment notes / rationale", value=selected_record["notes"] or "", key="edit_notes"
        )
        save_details = st.form_submit_button("Update saved details")

    if save_details:
        try:
            update_stock_details(
                user_id,
                watchlist_id,
                selected_symbol,
                {
                    "entry_price": edit_entry or None,
                    "stop_loss": edit_stop or None,
                    "target_price": edit_target or None,
                    "quantity": edit_quantity or None,
                    "investment_type": edit_type,
                    "purchase_date": edit_date.isoformat() if edit_date else None,
                    "notes": edit_notes.strip(),
                    "status": edit_status,
                },
            )
            st.success(f"Updated {selected_symbol}.")
        except (WatchlistError, ValueError) as exc:
            st.warning(str(exc))
        st.rerun()

    symbol_to_remove = st.selectbox(
        "Remove a saved symbol",
        options=[""] + saved_symbols,
        format_func=lambda value: "Select a symbol" if value == "" else value,
    )
    if st.button("Remove selected symbol", disabled=not symbol_to_remove):
        try:
            remove_symbol(user_id, watchlist_id, symbol_to_remove)
        except WatchlistError as exc:
            st.warning(str(exc))
        st.rerun()
