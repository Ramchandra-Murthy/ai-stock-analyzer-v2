"""Data Health: is the market-data provider serving NSE and BSE from this network?"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from components.disclaimer import show_disclaimer
from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES
from services.data_health import FAIL, PASS, best_form, measure_coverage, verdict
from services.resilient_market_data import download_symbol_frames

st.set_page_config(page_title="Data Health", page_icon="🩺", layout="wide")
st.title("🩺 Data Health")
show_disclaimer()
st.caption(
    "Checks what this machine can actually fetch. If BSE stocks are missing from a scan, the "
    "coverage test below shows whether the provider is returning them at all."
)

ICON = {PASS: "✅", "WARN": "⚠️", FAIL: "❌"}


@st.cache_resource(show_spinner=False)
def _providers_module():
    """Load scripts/check_providers.py (not a package) so the app and `make doctor` agree."""
    path = Path(__file__).resolve().parent.parent / "scripts" / "check_providers.py"
    spec = importlib.util.spec_from_file_location("check_providers", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_providers"] = module  # dataclasses look the module up here
    spec.loader.exec_module(module)
    return module


tab_cov, tab_checks = st.tabs(["Exchange coverage", "Provider checks"])

with tab_cov:
    depth = st.select_slider("Symbols to test per list", [8, 16, 24, 40, 80], value=24)
    if st.button("Run coverage test", type="primary"):
        pairs = list(zip(BSE_CANDIDATES, NSE_CANDIDATES, strict=True))[:depth]
        lists = {
            "NSE names (.NS)": [f"{name}.NS" for _, name in pairs],
            "BSE scrip codes (.BO)": [f"{code}.BO" for code, _ in pairs],
            "BSE names (.BO)": [f"{name}.BO" for _, name in pairs],
        }
        results = []
        with st.spinner("Downloading a month of daily bars for each list..."):
            for label, tickers in lists.items():
                results.append(
                    measure_coverage(
                        label,
                        tickers,
                        download_symbol_frames,
                        period="1mo",
                        interval="1d",
                        auto_adjust=False,
                        batch_size=8,
                        timeout=6,
                        retries=1,
                    )
                )
        st.session_state["dh_results"] = results

    results = st.session_state.get("dh_results")
    if not results:
        st.info("Press **Run coverage test**. It takes up to a minute.")
    else:
        cols = st.columns(len(results))
        for col, cov in zip(cols, results, strict=True):
            status, advice = verdict(cov)
            col.metric(f"{ICON[status]} {cov.label}", f"{cov.loaded}/{cov.tested}")
            col.caption(advice)
        winner = best_form(results[1:])
        if winner:
            st.success(f"For BSE, **{winner}** loads noticeably more symbols from this network.")
        missing = {c.label: list(c.missing) for c in results if c.missing}
        if missing:
            with st.expander("Symbols that returned no data"):
                longest = max(len(v) for v in missing.values())
                st.dataframe(
                    pd.DataFrame({k: v + [""] * (longest - len(v)) for k, v in missing.items()}),
                    use_container_width=True,
                    hide_index=True,
                )

with tab_checks:
    st.caption("The same checks as `make doctor`. Secret values are never shown.")
    if st.button("Run provider checks"):
        module = _providers_module()
        with st.spinner("Running checks..."):
            checks = [module.run_check(name, fn) for name, fn in module.CHECKS]
        st.session_state["dh_checks"] = checks
        st.session_state["dh_summary"] = module.summarize(checks)
    for result in st.session_state.get("dh_checks", []):
        st.markdown(f"{ICON.get(result.status, '•')} **{result.name}**: {result.detail}")
    if st.session_state.get("dh_summary"):
        st.info(st.session_state["dh_summary"])
