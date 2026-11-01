"""Interactive CSV-driven sentiment robustness research report."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.sentiment_robustness_diagnostics import evaluate_sentiment_robustness_grid
from ai_trading.sentiment_robustness_report import (
    load_news_records,
    load_price_bars,
    validate_coverage,
)
from components.disclaimer import show_disclaimer

st.set_page_config(page_title="Sentiment Robustness", page_icon="🧪", layout="wide")
st.title("🧪 Sentiment Robustness Report")
show_disclaimer()
st.warning(
    "Research-only sensitivity analysis. This report does not optimize parameters, "
    "produce live signals, or place orders."
)

with st.expander("CSV format"):
    st.markdown(
        "**News CSV** columns: `symbol,title,source,published_at,sentiment_score` "
        "(optional: `url`). Published timestamps should include a timezone.\n\n"
        "**Price CSV** columns: `symbol,timestamp,Close`. Use one row per symbol "
        "and timestamp; timestamps should include a timezone."
    )
    st.caption(
        "Use historical, point-in-time news and matching price bars. The report cannot "
        "verify whether uploaded news timestamps or sentiment scores are authentic."
    )

news_file = st.file_uploader("Upload sentiment news CSV", type=["csv"], key="sentiment_robust_news")
prices_file = st.file_uploader(
    "Upload historical price bars CSV", type=["csv"], key="sentiment_robust_prices"
)

col1, col2, col3 = st.columns(3)
horizons = col1.multiselect("Holding horizons (bars)", [3, 5, 10, 15, 20], default=[3, 5, 10])
thresholds = col2.multiselect(
    "Absolute sentiment thresholds", [0.1, 0.2, 0.3, 0.4, 0.5], default=[0.1, 0.2, 0.3]
)
costs = col3.multiselect(
    "Round-trip cost (bps per side)", [5.0, 10.0, 15.0, 20.0, 30.0], default=[5.0, 10.0, 20.0]
)
folds = st.slider("Chronological event folds", min_value=2, max_value=8, value=4)

if st.button(
    "Run robustness report", type="primary", disabled=news_file is None or prices_file is None
):
    try:
        news_frame = pd.read_csv(news_file)
        price_frame = pd.read_csv(prices_file)
        records = load_news_records(news_frame)
        bars_by_symbol = load_price_bars(price_frame)
        matched = validate_coverage(records, bars_by_symbol)
        if matched == 0:
            st.error("No uploaded news symbols match the price-bar symbols.")
        elif not horizons or not thresholds or not costs:
            st.error("Select at least one value in each parameter grid.")
        else:
            with st.spinner("Evaluating chronological folds across parameter combinations..."):
                report = evaluate_sentiment_robustness_grid(
                    records,
                    bars_by_symbol,
                    horizons=horizons,
                    sentiment_thresholds=thresholds,
                    transaction_costs_bps=costs,
                    folds=folds,
                )
            st.session_state["sentiment_robustness_report"] = report
            st.session_state["sentiment_robustness_coverage"] = (matched, len(records))
    except (ValueError, KeyError, pd.errors.ParserError) as exc:
        st.error(str(exc))

report = st.session_state.get("sentiment_robustness_report")
if isinstance(report, pd.DataFrame):
    matched, total = st.session_state.get("sentiment_robustness_coverage", (0, 0))
    st.caption(f"News rows with matching price symbols: {matched}/{total}")
    if report.empty:
        st.info("No eligible events were produced for these inputs and settings.")
    else:
        k1, k2, k3 = st.columns(3)
        k1.metric("Parameter combinations", len(report))
        k2.metric("Mean positive-fold rate", f"{report['positive_fold_rate'].mean():.1%}")
        k3.metric("Worst fold return", f"{report['worst_fold_return'].min():.2%}")
        st.subheader("Parameter sensitivity")
        st.dataframe(
            report.sort_values(
                ["positive_fold_rate", "worst_fold_return", "mean_fold_return"],
                ascending=False,
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.subheader("Fold stability")
        chart = report.pivot_table(
            index="horizon",
            columns="sentiment_threshold",
            values="positive_fold_rate",
            aggfunc="mean",
        )
        st.dataframe(chart.style.format("{:.1%}"), use_container_width=True)
        st.download_button(
            "Download robustness CSV",
            report.to_csv(index=False).encode("utf-8"),
            "sentiment_robustness_report.csv",
            "text/csv",
        )
