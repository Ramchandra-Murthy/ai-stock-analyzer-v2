"""Advanced Portfolio Lab: efficient frontier, Black-Litterman, tail risk, Monte Carlo, stress."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.lab_inputs import parse_holdings, parse_views
from algorithmic_trading.portfolio_advanced import (
    DEFAULT_RISK_AVERSION,
    DEFAULT_TAU,
    black_litterman_portfolio,
    efficient_frontier,
)
from algorithmic_trading.portfolio_optimizer import TRADING_DAYS, covariance
from algorithmic_trading.risk_advanced import (
    DEFAULT_MARKET_SHOCKS,
    advanced_risk_summary,
    monte_carlo_paths,
    path_quantiles,
    stress_test,
    summarise_paths,
    worst_windows,
)
from algorithmic_trading.risk_metrics import portfolio_returns
from services.cached_download import cached_download

st.set_page_config(page_title="Advanced Portfolio Lab", page_icon="🧮", layout="wide")
st.title("🧮 Advanced Portfolio Lab")
st.warning(
    "RESEARCH ONLY — every number here is an estimate fitted to past prices. Expected returns "
    "are the noisiest input, tails are heavier than any model assumes, and stress results are "
    "linear approximations. Not advice."
)

DEFAULT_HOLDINGS = "RELIANCE 30\nTCS 25\nHDFCBANK 25\nITC 10\nINFY 10"
DEFAULT_VIEWS = "TCS>INFY 0.03 0.5"


@st.cache_data(ttl=600, show_spinner=False)
def _returns(symbols: tuple[str, ...], period: str) -> pd.DataFrame:
    tickers = [f"{s}.NS" for s in symbols]
    raw = cached_download(tickers, period=period, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        return pd.DataFrame()
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    if not isinstance(raw.columns, pd.MultiIndex):
        close.columns = tickers[:1]
    close.columns = [str(c).removesuffix(".NS") for c in close.columns]
    return close.pct_change().dropna(how="all")


holdings_text = st.text_area(
    "Holdings: one `SYMBOL weight` per line (NSE symbols, weights are relative)",
    DEFAULT_HOLDINGS,
)
period = st.selectbox("History", ["2y", "5y", "10y"], index=1)

if st.button("Load data", type="primary"):
    try:
        holdings = parse_holdings(holdings_text)
        if len(holdings) < 2:
            raise ValueError("Enter at least two holdings.")
        data = _returns(tuple(holdings), period).dropna()
        if data.empty:
            raise ValueError("No price data came back. Try again shortly.")
        missing = [s for s in holdings if s not in data.columns]
        if missing:
            raise ValueError(f"No price data for: {', '.join(missing)}")
        if len(data) < 120:
            raise ValueError("Fewer than 120 shared trading days; use a longer history.")
        st.session_state["apl_returns"] = data[list(holdings)]
        st.session_state["apl_weights"] = holdings
    except ValueError as exc:
        st.session_state.pop("apl_returns", None)
        st.error(str(exc))

returns: pd.DataFrame | None = st.session_state.get("apl_returns")
weights: dict[str, float] | None = st.session_state.get("apl_weights")
if returns is None or weights is None:
    st.info("Enter your holdings and press **Load data** to begin.")
    st.stop()

first, last = returns.index[0], returns.index[-1]
st.caption(f"{len(returns)} shared trading days, {first:%d %b %Y} to {last:%d %b %Y}.")

mean = returns.mean() * TRADING_DAYS
cov = covariance(returns)

tab_frontier, tab_bl, tab_tail, tab_mc, tab_stress = st.tabs(
    ["Efficient frontier", "Black-Litterman", "Tail risk", "Monte Carlo", "Stress test"]
)

with tab_frontier:
    cap = st.slider("Maximum weight per stock", 0.2, 1.0, 0.5, 0.05, key="apl_cap")
    rf = st.number_input("Risk-free rate (annual)", 0.0, 0.2, 0.07, 0.005, key="apl_rf")
    try:
        points, frontier_weights = efficient_frontier(mean, cov, max_weight=cap, rf=rf)
    except ValueError as exc:
        st.error(str(exc))
    else:
        st.scatter_chart(points, x="volatility", y="return")
        best = int(points["sharpe"].idxmax())
        pick = st.slider("Frontier point", 0, len(points) - 1, best, key="apl_pick")
        row = points.iloc[pick]
        c1, c2, c3 = st.columns(3)
        c1.metric("Expected return", f"{row['return']:.1%}")
        c2.metric("Volatility", f"{row['volatility']:.1%}")
        c3.metric("Sharpe", f"{row['sharpe']:.2f}")
        st.dataframe(
            frontier_weights.iloc[[pick]].T.rename(columns={pick: "weight"}).style.format("{:.1%}"),
            use_container_width=True,
        )
        st.caption(
            "Expected returns are each stock's own historical mean, so the right-hand end of the "
            "frontier simply chases past winners. Prefer points near the minimum-variance end."
        )

with tab_bl:
    st.markdown(
        "Your holdings weights act as the **market portfolio**. Add views, one per line: "
        "`TCS 0.15 0.6` (TCS returns 15% a year, 60% confident) or "
        "`TCS>INFY 0.03 0.5` (TCS beats INFY by 3% a year, 50% confident)."
    )
    views_text = st.text_area("Views", DEFAULT_VIEWS, key="apl_views")
    b1, b2, b3 = st.columns(3)
    risk_aversion = b1.number_input("Risk aversion", 0.5, 10.0, DEFAULT_RISK_AVERSION, 0.5)
    tau = b2.number_input("Tau (prior uncertainty)", 0.01, 0.5, DEFAULT_TAU, 0.01)
    bl_cap = b3.slider("Maximum weight per stock", 0.2, 1.0, 0.5, 0.05, key="apl_blcap")
    try:
        result = black_litterman_portfolio(
            cov,
            weights,
            parse_views(views_text),
            tau=float(tau),
            risk_aversion=float(risk_aversion),
            max_weight=bl_cap,
        )
    except ValueError as exc:
        st.error(str(exc))
    else:
        table = pd.DataFrame(
            {
                "Market weight": pd.Series(weights, dtype=float) / sum(weights.values()),
                "Prior return": result["prior"],
                "Posterior return": result["posterior"],
                "BL weight": result["weights"],
            }
        )
        st.dataframe(
            table.style.format("{:.1%}"),
            use_container_width=True,
        )
        st.bar_chart(table[["Market weight", "BL weight"]])
        st.caption(
            "With no views the posterior equals the prior. Confident views move the weights "
            "toward them; the result is only as good as the views you supply."
        )

with tab_tail:
    try:
        summary = advanced_risk_summary(returns, weights)
        port = portfolio_returns(returns, weights)
    except ValueError as exc:
        st.error(str(exc))
    else:
        t1, t2, t3, t4 = st.columns(4)
        t1.metric("VaR 95% (Cornish-Fisher)", f"{summary['var_95_cornish_fisher']:.2%}")
        t2.metric("VaR 99% (Cornish-Fisher)", f"{summary['var_99_cornish_fisher']:.2%}")
        t3.metric("CVaR 95%", f"{summary['cvar_95']:.2%}")
        t4.metric("Max drawdown", f"{summary['max_drawdown']:.1%}")
        compare = pd.DataFrame(
            {
                "Historical": [summary["var_95_historical"], summary["var_99_historical"]],
                "Parametric": [summary["var_95_parametric"], summary["var_99_parametric"]],
                "Cornish-Fisher": [
                    summary["var_95_cornish_fisher"],
                    summary["var_99_cornish_fisher"],
                ],
            },
            index=["95%", "99%"],
        )
        st.markdown("**One-day VaR by method** (loss as a share of the portfolio)")
        st.dataframe(compare.style.format("{:.2%}"), use_container_width=True)
        s1, s2, s3 = st.columns(3)
        s1.metric("Skewness", f"{summary['skewness']:.2f}")
        s2.metric("Excess kurtosis", f"{summary['excess_kurtosis']:.2f}")
        s3.metric("Diversification ratio", f"{summary['diversification_ratio']:.2f}")
        window = st.slider("Window (trading days)", 1, 20, 5, key="apl_window")
        try:
            worst = worst_windows(port, window=window, count=5)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.markdown(f"**Worst non-overlapping {window}-day periods** (ending on)")
            st.dataframe(
                worst.rename("return").to_frame().style.format("{:.1%}"),
                use_container_width=True,
            )
        st.caption(
            "When Cornish-Fisher VaR sits well above the parametric figure, returns are skewed or "
            "fat-tailed and a normal model understates risk."
        )

with tab_mc:
    m1, m2, m3, m4 = st.columns(4)
    horizon = m1.slider("Horizon (trading days)", 21, 756, TRADING_DAYS, 21)
    n_paths = m2.select_slider("Paths", [500, 1000, 2000, 5000], value=2000)
    block = m3.slider("Block length (days)", 1, 20, 5)
    dd_limit = m4.slider("Drawdown limit", 0.05, 0.50, 0.20, 0.05)
    try:
        port = portfolio_returns(returns, weights)
        paths = monte_carlo_paths(port, horizon=horizon, n_paths=n_paths, block=block, seed=42)
        stats = summarise_paths(paths, dd_limit)
    except ValueError as exc:
        st.error(str(exc))
    else:
        st.markdown("**Growth of 1 — 5th, 50th and 95th percentile paths**")
        st.line_chart(path_quantiles(paths))
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Median outcome", f"{stats['terminal_median']:.2f}x")
        p2.metric("5th percentile", f"{stats['terminal_p5']:.2f}x")
        p3.metric("Chance of a loss", f"{stats['probability_of_loss']:.0%}")
        p4.metric(
            f"Chance of a {dd_limit:.0%}+ drawdown",
            f"{stats['probability_drawdown_beyond_limit']:.0%}",
        )
        st.caption(
            "Block bootstrap of your own history (fixed seed, so results are repeatable). It "
            "cannot produce a crash worse than the sample contains."
        )

with tab_stress:
    scenarios = dict(DEFAULT_MARKET_SHOCKS)
    custom = st.slider("Add a custom market shock", -0.60, 0.20, -0.15, 0.01, key="apl_shock")
    scenarios[f"Custom ({custom:+.0%})"] = custom
    try:
        stressed = stress_test(returns, weights, scenarios)
    except ValueError as exc:
        st.error(str(exc))
    else:
        st.dataframe(stressed.style.format("{:.1%}"), use_container_width=True)
        st.bar_chart(stressed["portfolio"])
        st.caption(
            "Each stock's loss is its weight x its beta to the equal-weight basket x the shock. "
            "In real sell-offs correlations rise and losses usually exceed this linear estimate."
        )
