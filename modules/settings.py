"""User-configurable preferences for the Streamlit dashboard.

Preferences are stored in Streamlit session state for the current session.
They are not persisted across sessions until a durable settings store is added.
"""

import streamlit as st  # noqa: I001

DEFAULT_SETTINGS = {
    "exchange": "NSE",
    "market_segment": "Equity / Cash",
    "universe": "NIFTY 50",
    "timeframe": "Daily",
    "ma_short": 20,
    "ma_long": 50,
    "ma_trend": 200,
    "rsi_period": 14,
    "min_price": 0.0,
    "min_volume": 0,
    "enable_price_alerts": False,
    "enable_signal_alerts": False,
    "refresh_minutes": 15,
    "theme_preference": "System default",
}


def _initialize_settings() -> None:
    """Populate missing session settings without overwriting user choices."""
    if "app_settings" not in st.session_state:
        st.session_state.app_settings = DEFAULT_SETTINGS.copy()


def show() -> None:
    """Render the Settings page and save changes to the current session."""
    _initialize_settings()
    settings = st.session_state.app_settings

    st.title("⚙ Settings")
    st.caption("Configure dashboard defaults and scanner preferences.")
    st.info(
        "Changes are saved for this Streamlit session. Persistent storage and "
        "automatic alert delivery are not enabled yet."
    )

    with st.form("settings_form"):
        market_tab, scanner_tab, analysis_tab, alerts_tab, app_tab = st.tabs(
            ["Market", "Scanner", "Technical Analysis", "Alerts", "Application"]
        )

        with market_tab:
            st.subheader("Market preferences")
            exchange = st.selectbox(
                "Default exchange",
                ["NSE", "BSE", "NSE + BSE"],
                index=["NSE", "BSE", "NSE + BSE"].index(settings["exchange"]),
            )
            market_segment = st.selectbox(
                "Default market segment",
                ["Equity / Cash", "Futures & Options", "All supported segments"],
                index=["Equity / Cash", "Futures & Options", "All supported segments"].index(
                    settings["market_segment"]
                ),
            )
            universe = st.selectbox(
                "Default stock universe",
                ["NIFTY 50", "NIFTY 500", "Watchlist", "All supported stocks"],
                index=["NIFTY 50", "NIFTY 500", "Watchlist", "All supported stocks"].index(
                    settings["universe"]
                ),
            )

        with scanner_tab:
            st.subheader("Scanner filters")
            min_price = st.number_input(
                "Minimum price (₹; 0 disables filter)",
                min_value=0.0,
                value=float(settings["min_price"]),
                step=1.0,
            )
            min_volume = st.number_input(
                "Minimum traded volume (0 disables filter)",
                min_value=0,
                value=int(settings["min_volume"]),
                step=1000,
            )
            refresh_minutes = st.selectbox(
                "Preferred refresh interval (minutes)",
                [5, 15, 30, 60],
                index=[5, 15, 30, 60].index(settings["refresh_minutes"]),
            )
            st.caption("These preferences take effect when connected to the scanner.")

        with analysis_tab:
            st.subheader("Technical indicator defaults")
            timeframe = st.selectbox(
                "Default chart timeframe",
                ["5-minute", "15-minute", "Hourly", "Daily", "Weekly"],
                index=["5-minute", "15-minute", "Hourly", "Daily", "Weekly"].index(
                    settings["timeframe"]
                ),
            )
            col1, col2, col3 = st.columns(3)
            ma_short = col1.number_input(
                "Short MA period",
                min_value=1,
                max_value=500,
                value=int(settings["ma_short"]),
                step=1,
            )
            ma_long = col2.number_input(
                "Long MA period",
                min_value=1,
                max_value=500,
                value=int(settings["ma_long"]),
                step=1,
            )
            ma_trend = col3.number_input(
                "Trend MA period",
                min_value=1,
                max_value=500,
                value=int(settings["ma_trend"]),
                step=1,
            )
            rsi_period = st.number_input(
                "RSI period",
                min_value=2,
                max_value=100,
                value=int(settings["rsi_period"]),
                step=1,
            )
            if not ma_short < ma_long < ma_trend:
                st.warning("For conventional short/long/trend ordering, use increasing MA periods.")

        with alerts_tab:
            st.subheader("Alert preferences")
            enable_price_alerts = st.checkbox(
                "Enable price-alert preference", value=bool(settings["enable_price_alerts"])
            )
            enable_signal_alerts = st.checkbox(
                "Enable technical-signal alert preference",
                value=bool(settings["enable_signal_alerts"]),
            )
            st.caption(
                "These switches record your preference only; they do not send notifications yet."
            )

        with app_tab:
            st.subheader("Application preferences")
            theme_preference = st.selectbox(
                "Appearance preference",
                ["System default", "Light", "Dark"],
                index=["System default", "Light", "Dark"].index(settings["theme_preference"]),
            )

        save_col, reset_col = st.columns(2)
        save_clicked = save_col.form_submit_button("Save settings", type="primary")
        reset_clicked = reset_col.form_submit_button("Reset to defaults")

    if save_clicked:
        st.session_state.app_settings = {
            "exchange": exchange,
            "market_segment": market_segment,
            "universe": universe,
            "timeframe": timeframe,
            "ma_short": int(ma_short),
            "ma_long": int(ma_long),
            "ma_trend": int(ma_trend),
            "rsi_period": int(rsi_period),
            "min_price": float(min_price),
            "min_volume": int(min_volume),
            "enable_price_alerts": enable_price_alerts,
            "enable_signal_alerts": enable_signal_alerts,
            "refresh_minutes": int(refresh_minutes),
            "theme_preference": theme_preference,
        }
        st.success("Settings saved for this session.")

    if reset_clicked:
        st.session_state.app_settings = DEFAULT_SETTINGS.copy()
        st.success("Settings reset to defaults. Rerun the page to refresh the form.")

    with st.expander("Current session settings"):
        st.json(st.session_state.app_settings)
