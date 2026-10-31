"""Mutual Fund Analysis: NAV history, returns, risk, SIP/SWP and goal planning (research only)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from mutual_funds.analytics import (
    capture_and_beta,
    compare_funds,
    lumpsum_value,
    required_sip,
    risk_metrics,
    rolling_returns,
    rolling_summary,
    sip_future_value,
    sip_simulation,
    swp_simulation,
    ter_drag,
    trailing_returns,
)
from mutual_funds.nav import fetch_scheme, is_direct_growth, search_schemes
from services.cached_download import cached_download

st.set_page_config(page_title="Mutual Fund Analysis", page_icon="🏦", layout="wide")
st.title("🏦 Mutual Fund Analysis")
st.warning(
    "RESEARCH ONLY — past returns do not predict future returns. NAV data comes from the free "
    "mfapi.in service (AMFI), may lag a day and is not verified here. Not investment advice; "
    "taxes, exit loads and fund-specific risks are not modelled."
)


@st.cache_data(ttl=3600, show_spinner=False)
def _search(query: str) -> pd.DataFrame:
    return search_schemes(query)


@st.cache_data(ttl=3600, show_spinner=False)
def _scheme(code: str):
    return fetch_scheme(code)


@st.cache_data(ttl=3600, show_spinner=False)
def _benchmark() -> pd.Series | None:
    raw = cached_download("^NSEI", period="max", progress=False)
    if raw is None or raw.empty:
        return None
    close = raw["Close"]
    return (close.iloc[:, 0] if isinstance(close, pd.DataFrame) else close).dropna()


tab_one, tab_cmp, tab_plan = st.tabs(["Single fund", "Compare funds", "Planner"])

with tab_one:
    query = st.text_input("Search fund name (3+ characters)", "mirae large midcap direct growth")
    if st.button("Search", key="search"):
        try:
            st.session_state["mf_results"] = _search(query)
            if st.session_state["mf_results"].empty:
                st.info(
                    "No schemes matched. Try fewer words, e.g. 'mirae large' or the fund house."
                )
        except Exception as exc:
            st.error(f"Search failed: {exc}")
    results = st.session_state.get("mf_results")
    if results is not None and not results.empty:
        choice = st.selectbox(
            "Scheme",
            list(results["schemeName"]),
            format_func=lambda n: ("⭐ " if is_direct_growth(n) else "") + n,
        )
        code = str(results.loc[results["schemeName"] == choice, "schemeCode"].iloc[0])
        years_back = st.slider("Use the last N years", 1, 20, 10)
        monthly = st.number_input("Monthly SIP (₹)", 500.0, value=10_000.0, step=500.0)
        step_up = st.slider("Yearly SIP step-up (%)", 0, 20, 0) / 100
        corpus = st.number_input("SWP corpus (₹)", 10_000.0, value=2_000_000.0, step=100_000.0)
        withdrawal = st.number_input("Monthly withdrawal (₹)", 500.0, value=15_000.0, step=500.0)
        if st.button("Analyse", type="primary"):
            st.session_state["mf_analyse"] = code
        if st.session_state.get("mf_analyse") == code:
            try:
                meta, nav = _scheme(code)
                nav = nav[nav.index >= nav.index[-1] - pd.DateOffset(years=years_back)]
                st.subheader(meta.get("scheme_name", choice))
                st.caption(
                    f"{meta.get('fund_house', '')} · {meta.get('scheme_category', '')} · "
                    f"{nav.index[0]:%d %b %Y} to {nav.index[-1]:%d %b %Y} · latest NAV {nav.iloc[-1]:,.2f}"
                )
                st.markdown("**Trailing returns**")
                st.dataframe(
                    trailing_returns(nav).style.format({"Return": "{:.1%}"}),
                    use_container_width=True,
                )
                risk = risk_metrics(nav)
                cols = st.columns(5)
                cols[0].metric("CAGR", f"{risk['cagr']:.1%}")
                cols[1].metric("Volatility", f"{risk['volatility']:.1%}")
                cols[2].metric("Sharpe", f"{risk['sharpe']:.2f}")
                cols[3].metric("Max drawdown", f"{risk['max_drawdown']:.1%}")
                rec = risk["recovery_days"]
                cols[4].metric("Recovery", "not yet" if rec != rec else f"{rec:.0f} days")
                st.markdown("**Growth of ₹100**")
                st.line_chart(nav / nav.iloc[0] * 100)
                try:
                    roll = rolling_returns(nav, 3)
                    s = rolling_summary(roll)
                    st.markdown("**Rolling 3-year returns (annualised)**")
                    st.line_chart(roll)
                    st.caption(
                        f"Range {s['min']:.1%} to {s['max']:.1%}, median {s['median']:.1%}; "
                        f"{s['share_negative']:.0%} of 3-year windows lost money."
                    )
                except ValueError:
                    st.info("Not enough history for rolling 3-year returns.")
                sip = sip_simulation(nav, float(monthly), step_up=step_up)
                lump = lumpsum_value(nav, float(sip["invested"]))
                st.markdown("**SIP on this fund's actual NAV history**")
                c = st.columns(4)
                c[0].metric("Invested", f"₹{sip['invested']:,.0f}")
                c[1].metric("Value today", f"₹{sip['final_value']:,.0f}")
                c[2].metric("SIP XIRR", f"{sip['xirr']:.1%}")
                c[3].metric("Same money as lumpsum at start", f"₹{lump['final_value']:,.0f}")
                swp = swp_simulation(nav, float(corpus), float(withdrawal))
                st.markdown("**Systematic withdrawals replayed on this NAV history**")
                c = st.columns(3)
                c[0].metric("Withdrawn", f"₹{swp['total_withdrawn']:,.0f}")
                c[1].metric("Remaining value", f"₹{swp['remaining_value']:,.0f}")
                c[2].metric(
                    "Corpus lasted",
                    "to the end" if swp["depleted_on"] is None else f"{swp['depleted_on']:%b %Y}",
                )
                bench = _benchmark()
                if bench is not None:
                    try:
                        cap = capture_and_beta(nav, bench)
                        st.markdown("**Versus NIFTY 50 (price index)**")
                        c = st.columns(4)
                        c[0].metric("Beta", f"{cap['beta']:.2f}")
                        c[1].metric("Alpha (annual)", f"{cap['alpha_annual']:.1%}")
                        c[2].metric("Upside capture", f"{cap['up_capture']:.0%}")
                        c[3].metric("Downside capture", f"{cap['down_capture']:.0%}")
                        st.caption(
                            "The benchmark here is the price index, not a total-return index, "
                            "so alpha is understated. Debt and hybrid funds need other benchmarks."
                        )
                    except ValueError as exc:
                        st.info(str(exc))
            except Exception as exc:
                st.error(f"Could not analyse this scheme: {exc}")

with tab_cmp:
    codes = st.text_input("Scheme codes (comma separated, from the search above)", "118834,120503")
    if st.button("Compare", key="cmp"):
        try:
            navs = {}
            for c in [x.strip() for x in codes.split(",") if x.strip()]:
                meta, nav = _scheme(c)
                navs[str(meta.get("scheme_name", c))[:45]] = nav
            st.dataframe(
                compare_funds(navs).style.format(
                    {
                        "CAGR": "{:.1%}",
                        "Volatility": "{:.1%}",
                        "Sharpe": "{:.2f}",
                        "Sortino": "{:.2f}",
                        "Max drawdown": "{:.1%}",
                    }
                ),
                use_container_width=True,
            )
            st.line_chart(
                pd.concat({k: v / v.iloc[0] * 100 for k, v in navs.items()}, axis=1).dropna()
            )
        except Exception as exc:
            st.error(f"Comparison failed: {exc}")

with tab_plan:
    st.markdown("**Goal planner** (assumes a constant return, which real funds do not deliver)")
    c1, c2 = st.columns(2)
    with c1:
        target = st.number_input("Target corpus (₹)", 100_000.0, value=10_000_000.0, step=100_000.0)
        years = st.slider("Years", 1, 40, 15)
    with c2:
        ret = st.slider("Assumed annual return (%)", 4.0, 18.0, 11.0, 0.5) / 100
        su = st.slider("Yearly step-up (%)", 0, 20, 5, key="plan_su") / 100
    need = required_sip(target, years, ret, su)
    st.metric("Starting monthly SIP needed", f"₹{need:,.0f}")
    low, high = required_sip(target, years, ret - 0.03, su), required_sip(
        target, years, ret + 0.03, su
    )
    st.caption(
        f"If returns are 3 points lower the SIP needed is ₹{low:,.0f}; 3 points higher, ₹{high:,.0f}. "
        f"Check: ₹{need:,.0f} grows to ₹{sip_future_value(need, years, ret, su):,.0f}."
    )
    st.markdown("**Withdrawal plan on a past NAV series**")
    st.caption(
        "Use the Single fund tab to pick a scheme; the SWP calculator below uses a steady-growth assumption."
    )
    st.markdown("**Regular vs Direct plan cost**")
    c1, c2, c3 = st.columns(3)
    with c1:
        gross = st.slider("Gross return (%)", 5.0, 18.0, 12.0, 0.5) / 100
    with c2:
        t_reg = st.slider("Regular plan expense ratio (%)", 0.5, 2.5, 1.7, 0.05) / 100
    with c3:
        t_dir = st.slider("Direct plan expense ratio (%)", 0.1, 1.5, 0.6, 0.05) / 100
    try:
        d = ter_drag(years, gross, t_reg, t_dir)
        st.metric(
            f"Extra corpus from Direct over {years} years (per ₹1 lakh)", f"₹{d['difference']:,.0f}"
        )
    except ValueError as exc:
        st.error(str(exc))
