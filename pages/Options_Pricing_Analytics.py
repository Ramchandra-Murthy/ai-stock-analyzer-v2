"""Informational pricing analytics for provider-observed index option premiums."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from engine.nifty_options_pricing_analytics import analyze_observed_option
from components.disclaimer import show_disclaimer
from services.options_analytics import clear_option_chain_cache, fetch_option_chain_cached

st.set_page_config(page_title="Options Pricing Analytics", page_icon="🧮", layout="wide")
st.title("NIFTY Options Pricing Analytics")
show_disclaimer()
st.warning(
    "INFORMATIONAL ANALYSIS ONLY — theoretical prices and Greeks are not trade signals. "
    "This page never submits broker orders."
)
st.caption(
    "Implied volatility uses the provider-returned premium. Theoretical price and Greeks "
    "use your chosen volatility assumption. Verify provider data before relying on results."
)

underlying = st.selectbox("Underlying", ["NIFTY", "BANKNIFTY", "FINNIFTY"])
if st.button("Refresh option chain"):
    clear_option_chain_cache()
provider = fetch_option_chain_cached(underlying)

status_left, status_mid, status_right = st.columns(3)
status_left.metric("Provider", provider.provider_symbol)
status_mid.metric("Data status", provider.status)
status_right.metric(
    "Spot",
    f"{provider.spot:.2f}" if provider.spot is not None else "Unavailable",
)
st.caption(provider.message)
retrieved_at = datetime.now(ZoneInfo("Asia/Kolkata"))
st.caption(
    f"Retrieved by app at {retrieved_at.strftime('%Y-%m-%d %H:%M:%S %Z')}; "
    "this is not an exchange-provided quote timestamp."
)

if provider.status != "AVAILABLE" or provider.spot is None or provider.chain.empty:
    st.warning("Pricing analytics are disabled until valid provider data is available.")
    st.stop()

expiry_options = list(provider.expiries) or ([provider.expiry] if provider.expiry else [])
if not expiry_options:
    st.warning("The provider did not return an expiry date.")
    st.stop()

default_expiry_index = (
    expiry_options.index(provider.expiry) if provider.expiry in expiry_options else 0
)
selected_expiry = st.selectbox(
    "Option expiry (provider-reported)",
    expiry_options,
    index=default_expiry_index,
)
if selected_expiry != provider.expiry:
    provider = fetch_option_chain_cached(underlying, selected_expiry)
    if (
        provider.status != "AVAILABLE"
        or provider.spot is None
        or provider.chain.empty
        or provider.expiry != selected_expiry
    ):
        st.warning("The selected expiry's option chain is unavailable. No estimates were produced.")
        st.stop()

if "strike" not in provider.chain.columns:
    st.warning("The normalized provider chain has no strike column.")
    st.stop()

strike_values = pd.to_numeric(provider.chain["strike"], errors="coerce").dropna().unique().tolist()
strike_values = sorted(float(value) for value in strike_values if float(value) > 0)
if not strike_values:
    st.warning("No valid strike values are available from the provider.")
    st.stop()

left, right = st.columns(2)
with left:
    option_type = st.radio("Option type", ["call", "put"], horizontal=True)
    strike = st.selectbox("Strike", strike_values)
with right:
    risk_free_rate_pct = st.number_input(
        "Risk-free rate (% annual; assumption)",
        min_value=0.0,
        max_value=20.0,
        value=6.0,
        step=0.25,
    )
    model_volatility_pct = st.number_input(
        "Model volatility (% annual; assumption)",
        min_value=0.1,
        max_value=300.0,
        value=20.0,
        step=1.0,
    )

premium_column = "CE LTP" if option_type == "call" else "PE LTP"
if premium_column not in provider.chain.columns:
    st.warning(f"Provider data is missing the {premium_column} field.")
    st.stop()

strike_rows = provider.chain.loc[
    pd.to_numeric(provider.chain["strike"], errors="coerce") == float(strike)
]
if strike_rows.empty:
    st.warning("The selected strike is not present in the current provider chain.")
    st.stop()

observed_premium = pd.to_numeric(strike_rows.iloc[0][premium_column], errors="coerce")
if pd.isna(observed_premium) or float(observed_premium) <= 0:
    st.warning("A positive, valid provider premium is required to calculate implied volatility.")
    st.stop()

expiry_date = date.fromisoformat(selected_expiry)
today_ist = datetime.now(ZoneInfo("Asia/Kolkata")).date()
days_to_expiry = (expiry_date - today_ist).days
if days_to_expiry <= 0:
    st.warning(
        "Implied volatility is unavailable for an expired or same-day expiry in this date-based model."
    )
    st.stop()

time_to_expiry = days_to_expiry / 365.0
st.caption(
    f"Time to expiry: {days_to_expiry} calendar days (days ÷ 365 approximation). "
    "The adapter does not supply an exact contract expiry time."
)

try:
    snapshot = analyze_observed_option(
        spot=float(provider.spot),
        strike=float(strike),
        time_to_expiry=time_to_expiry,
        risk_free_rate=risk_free_rate_pct / 100.0,
        observed_premium=float(observed_premium),
        model_volatility=model_volatility_pct / 100.0,
        option_type=option_type,
    )
except (ValueError, RuntimeError, OverflowError) as exc:
    st.warning(f"Pricing analytics could not be calculated: {exc}")
    st.stop()

st.subheader("Observed premium and model estimate")
premium_left, premium_mid, premium_right = st.columns(3)
premium_left.metric("Observed provider premium", f"₹{snapshot.observed_premium:.2f}")
premium_mid.metric("Model theoretical premium", f"₹{snapshot.model_result.price:.2f}")
premium_right.metric("Implied volatility", f"{snapshot.implied_volatility:.2%}")
st.caption(
    "Theoretical premium uses the volatility assumption above; implied volatility is solved "
    "separately from the observed premium. Differences are model comparisons, not buy/sell advice."
)

st.subheader("Greeks (using the chosen model volatility)")
greek_columns = st.columns(5)
greeks = [
    ("Delta", snapshot.model_result.delta),
    ("Gamma", snapshot.model_result.gamma),
    ("Vega", snapshot.model_result.vega),
    ("Theta / year", snapshot.model_result.theta),
    ("Rho", snapshot.model_result.rho),
]
for column, (label, value) in zip(greek_columns, greeks, strict=True):
    column.metric(label, f"{value:.6f}")

st.caption(
    "Vega and rho are sensitivities to a 1.00 change in volatility and rate; theta is per year. "
    "The model assumes European exercise, constant rates and volatility, and no discrete dividends."
)

st.subheader("Spot / volatility / time scenarios")
scenario_rows = [
    {
        "Spot": scenario.spot,
        "Volatility": f"{scenario.volatility:.2%}",
        "Time to expiry (days)": round(scenario.time_to_expiry * 365.0, 2),
        "Theoretical premium": round(scenario.result.price, 4),
        "Delta": round(scenario.result.delta, 6),
        "Gamma": round(scenario.result.gamma, 8),
        "Vega": round(scenario.result.vega, 6),
        "Theta / year": round(scenario.result.theta, 6),
        "Rho": round(scenario.result.rho, 6),
    }
    for scenario in snapshot.scenarios
]
st.dataframe(pd.DataFrame(scenario_rows), use_container_width=True, hide_index=True)
st.caption(
    "Scenarios are deterministic what-if calculations, not forecasts. They vary spot by ±1%, "
    "volatility by ±5 percentage points (with a positive floor), and time to expiry by halving it."
)
