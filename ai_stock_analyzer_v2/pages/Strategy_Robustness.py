"""Strategy Robustness: bootstrap confidence intervals and the deflated Sharpe ratio."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.robustness import (
    bootstrap_metrics,
    deflated_sharpe,
    probabilistic_sharpe,
)
from algorithmic_trading.strategy_lab import normalise_price_frame, run_strategy_lab
from algorithmic_trading.trading_costs import india_cost_model
from algorithmic_trading.walk_forward_optimizer import (
    PARAM_GRIDS,
    parameter_combinations,
    sharpe,
)
from services.resilient_market_data import download_market_frames

st.set_page_config(page_title="Strategy Robustness", page_icon="🎲", layout="wide")
st.title("🎲 Strategy Robustness")
st.warning("RESEARCH ONLY — statistics on past returns; not a forecast or advice.")
st.caption(
    "A single backtest is one draw from a noisy process. Resampling shows how wide the range of "
    "outcomes could be, and the deflated Sharpe ratio discounts the best result among many "
    "parameter variants tried."
)


@st.cache_data(ttl=300, show_spinner=False)
def _load(ticker: str, period: str) -> pd.DataFrame | None:
    frames, _ = download_market_frames([ticker], period=period, interval="1d")
    frame = frames.get(ticker.upper())
    return None if frame is None or frame.empty else frame


c1, c2 = st.columns(2)
with c1:
    symbol = st.text_input("NSE symbol", "RELIANCE").strip().upper()
    period = st.selectbox("History", ["5y", "10y"], index=1)
with c2:
    strategy = st.selectbox("Strategy (best-of-grid is tested)", list(PARAM_GRIDS))
    n_boot = st.slider("Bootstrap samples", 200, 3000, 1000, 100)

if st.button("Run robustness check", type="primary"):
    raw = _load(f"{symbol}.NS", period)
    if raw is None:
        st.error(f"No data returned for {symbol}.")
        st.stop()
    model = india_cost_model("delivery", slippage_bps=5.0)
    try:
        prices = normalise_price_frame(raw)
        runs = []
        for params in parameter_combinations(strategy):
            res = run_strategy_lab(prices, strategy, cost_model=model, params=params)
            runs.append(
                (params, res.curve["strategy_return"], sharpe(res.curve["strategy_return"]))
            )
        best_params, best_returns, best_sharpe = max(runs, key=lambda r: r[2])
        boot = bootstrap_metrics(best_returns, n_boot=int(n_boot))
        psr = probabilistic_sharpe(best_returns)
        dsr = deflated_sharpe(best_returns, [r[2] for r in runs])
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    st.subheader(f"{symbol} — best {strategy} variant of {len(runs)} tried")
    st.caption("Parameters: " + ", ".join(f"{k}={v:g}" for k, v in best_params.items()))
    cols = st.columns(4)
    cols[0].metric("Sharpe (best variant)", f"{best_sharpe:.2f}")
    cols[1].metric("Chance Sharpe > 0", f"{psr:.0%}")
    cols[2].metric("Deflated Sharpe confidence", f"{dsr:.0%}")
    cols[3].metric("Chance of losing money", f"{boot['prob_loss']:.0%}")
    if dsr < 0.95:
        st.warning(
            f"After accounting for {len(runs)} variants tried, confidence that the edge is real is "
            f"{dsr:.0%} (under 95%): this result may simply be the luckiest of the grid."
        )
    else:
        st.success("The edge survives the multiple-testing adjustment (still historical).")
    table = pd.DataFrame(
        {
            "5th pct": [boot["sharpe"]["p5"], boot["cagr"]["p5"], boot["max_drawdown"]["p5"]],
            "Median": [
                boot["sharpe"]["median"],
                boot["cagr"]["median"],
                boot["max_drawdown"]["median"],
            ],
            "95th pct": [boot["sharpe"]["p95"], boot["cagr"]["p95"], boot["max_drawdown"]["p95"]],
        },
        index=["Sharpe", "CAGR", "Max drawdown"],
    )
    st.markdown("**Bootstrap range of outcomes (block resampling of daily returns)**")
    st.dataframe(table.style.format("{:.2f}"), use_container_width=True)
