"""Walk-Forward Lab: honest out-of-sample testing of tuned strategies."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.strategy_lab import normalise_price_frame
from algorithmic_trading.trading_costs import RATES_VERIFIED, india_cost_model
from algorithmic_trading.walk_forward_optimizer import (
    PARAM_GRIDS,
    parameter_surface,
    surface_robustness,
    walk_forward_optimize,
)
from services.resilient_market_data import download_market_frames

st.set_page_config(page_title="Walk-Forward Lab", page_icon="🔬", layout="wide")

st.title("🔬 Walk-Forward Lab")
st.warning(
    "RESEARCH ONLY — out-of-sample results are still historical and are not forecasts. "
    "This page never places orders."
)
st.caption(
    "Tuning parameters on all history and reporting that same history is overfitting. Here the "
    "parameters are re-chosen in every window using only the data before it, then scored on the "
    "window that follows. The stitched out-of-sample curve is the number to trust."
)


@st.cache_data(ttl=300, show_spinner=False)
def _load_prices(ticker: str, period: str) -> tuple[pd.DataFrame | None, str]:
    frames, diagnostics = download_market_frames([ticker], period=period, interval="1d")
    frame = frames.get(ticker.upper())
    if frame is None or frame.empty:
        return None, f"No data returned for {ticker}. Missing: {diagnostics.get('missing')}"
    return frame, ""


def _pct(value: float) -> str:
    return f"{value:.1%}"


left, right = st.columns(2)
with left:
    exchange = st.selectbox("Exchange", ["NSE", "BSE"])
    symbol = st.text_input("Symbol", "RELIANCE")
    period = st.selectbox("History", ["5y", "10y"], index=1)
    strategy = st.selectbox("Strategy", list(PARAM_GRIDS))
with right:
    train_bars = st.number_input("Train window (trading days)", 100, 2000, 504, 21)
    test_bars = st.number_input("Test window (trading days)", 21, 500, 126, 21)
    anchored = st.checkbox("Anchored (train always starts at the first bar)", value=False)
    use_nse_costs = st.checkbox(
        "Use NSE delivery costs + 5 bps slippage",
        value=True,
        help=f"Statutory rates verified {RATES_VERIFIED}; otherwise a flat 10 bps per side.",
    )

grid = PARAM_GRIDS[strategy]
names = list(grid)
x_param = st.selectbox("Heatmap x-axis", names, index=0)
y_param = st.selectbox("Heatmap y-axis", names, index=min(1, len(names) - 1))

if st.button("Run walk-forward", type="primary"):
    symbol = symbol.strip().upper()
    if not symbol:
        st.error("Enter a symbol.")
        st.stop()
    ticker = f"{symbol}.{'NS' if exchange == 'NSE' else 'BO'}"
    with st.spinner(f"Loading {ticker}..."):
        raw, error = _load_prices(ticker, period)
    if raw is None:
        st.error(error)
        st.stop()

    cost_model = india_cost_model("delivery", slippage_bps=5.0) if use_nse_costs else None
    try:
        prices = normalise_price_frame(raw)
        with st.spinner("Testing every parameter set in every window..."):
            result = walk_forward_optimize(
                prices,
                strategy,
                train_bars=int(train_bars),
                test_bars=int(test_bars),
                anchored=anchored,
                cost_bps=10.0,
                cost_model=cost_model,
            )
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    st.subheader(f"{ticker} — {strategy}")
    cols = st.columns(4)
    cols[0].metric(
        "Out-of-sample return",
        _pct(result.oos["total_return"]),
        f"buy & hold {_pct(result.buy_hold['total_return'])}",
    )
    cols[1].metric(
        "Out-of-sample Sharpe",
        f"{result.oos['sharpe']:.2f}",
        f"buy & hold {result.buy_hold['sharpe']:.2f}",
    )
    cols[2].metric("Max drawdown", _pct(result.oos["max_drawdown"]))
    cols[3].metric("Same choice in", _pct(result.parameter_stability), "of windows")

    gap = result.mean_train_sharpe - result.mean_test_sharpe
    if result.mean_train_sharpe > 0 and result.mean_test_sharpe <= 0:
        st.error(
            f"Train Sharpe averaged {result.mean_train_sharpe:.2f} but test Sharpe "
            f"{result.mean_test_sharpe:.2f}: the tuned edge did not survive out of sample."
        )
    elif gap > 1.0:
        st.warning(
            f"Large train-to-test gap ({result.mean_train_sharpe:.2f} → "
            f"{result.mean_test_sharpe:.2f}): a sign of overfitting."
        )
    else:
        st.info(
            f"Mean Sharpe train {result.mean_train_sharpe:.2f}, test {result.mean_test_sharpe:.2f}."
        )

    curve = pd.DataFrame(
        {
            "Walk-forward (out of sample)": (1.0 + result.oos_returns).cumprod(),
            "Buy & hold (same dates)": (1.0 + result.buy_hold_returns).cumprod(),
        }
    )
    st.markdown("**Out-of-sample growth of 1**")
    st.line_chart(curve)

    st.markdown("**Window by window**")
    st.dataframe(
        result.windows.style.format(
            {"train_sharpe": "{:.2f}", "test_sharpe": "{:.2f}", "test_return": "{:.1%}"}
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("**Parameter stability (full-history Sharpe)**")
    if x_param == y_param:
        st.info("Pick two different parameters for the heatmap.")
    else:
        try:
            surface = parameter_surface(
                prices, strategy, x_param, y_param, cost_bps=10.0, cost_model=cost_model
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            try:
                styled = surface.style.background_gradient(cmap="RdYlGn", axis=None).format(
                    "{:.2f}", na_rep="–"
                )
            except ImportError:  # matplotlib is optional for the colouring only
                styled = surface.style.format("{:.2f}", na_rep="–")
            st.dataframe(styled, use_container_width=True)
            rob = surface_robustness(surface)
            st.caption(
                f"{rob['share_positive']:.0%} of settings had a positive Sharpe (median "
                f"{rob['median']:.2f}, best {rob['best']:.2f}). A broad green area suggests a "
                "robust idea; one isolated green cell is probably luck. This grid is full "
                "history, so it describes stability, not out-of-sample performance."
            )
