"""Advanced Portfolio Lab: efficient frontier, Black-Litterman, tail risk, Monte Carlo, stress."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithmic_trading.lab_inputs import (
    parse_holdings,
    parse_share_counts,
    parse_views,
    resolve_holdings,
)
from algorithmic_trading.portfolio_advanced import (
    DEFAULT_RISK_AVERSION,
    DEFAULT_TAU,
    black_litterman_portfolio,
    efficient_frontier,
)
from algorithmic_trading.portfolio_optimizer import TRADING_DAYS, covariance
from algorithmic_trading.portfolio_tools import min_cvar_weights, portfolio_cvar, rebalance_plan
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
from services.price_table import load_close_prices, load_returns

st.set_page_config(page_title="Advanced Portfolio Lab", page_icon="🧮", layout="wide")
st.title("🧮 Advanced Portfolio Lab")
st.warning(
    "RESEARCH ONLY — every number here is an estimate fitted to past prices. Expected returns "
    "are the noisiest input, tails are heavier than any model assumes, and stress results are "
    "linear approximations. Not advice."
)

DEFAULT_HOLDINGS = "RELIANCE 30\nTCS 25\nHDFCBANK 25\nITC 10\nINFY 10"
VIEWS_EXAMPLE = "TCS>INFY 0.03 0.5"


@st.cache_data(ttl=600, show_spinner=False)
def _returns(items: tuple[tuple[str, str], ...], period: str):
    """Daily returns per display name; also the names that had no data at all."""
    return load_returns(dict(items), period, min_rows=120)


@st.cache_data(ttl=120, show_spinner=False)
def _last_prices(items: tuple[tuple[str, str], ...]) -> dict[str, float]:
    close, missing = load_close_prices(dict(items), "5d")
    if missing:
        raise ValueError(f"No recent price for: {', '.join(missing)}")
    return {name: float(close[name].dropna().iloc[-1]) for name in close.columns}


holdings_text = st.text_area(
    "Holdings: one `SYMBOL weight` per line (weights are relative). Accepts `TCS`, `TCS.NS`, "
    "`NSE:TCS`, BSE scrip codes like `500325` or `BSE:500325`, and `.BO` tickers.",
    DEFAULT_HOLDINGS,
)
c_ex, c_period = st.columns(2)
default_exchange = c_ex.selectbox(
    "Exchange for plain names", ["NSE", "BSE"], help="Used for symbols with no NSE:/BSE: prefix."
)
period = c_period.selectbox("History", ["2y", "5y", "10y"], index=1)

if st.button("Load data", type="primary"):
    try:
        typed = parse_holdings(holdings_text)
        if len(typed) < 2:
            raise ValueError("Enter at least two holdings.")
        ticker_by_name, holdings = resolve_holdings(typed, default_exchange)
        data, missing = _returns(tuple(ticker_by_name.items()), period)
        if missing:
            st.warning(
                f"No price history for {', '.join(missing)}; they were left out. Check the "
                "symbol and exchange, or try again if the data provider was busy."
            )
        if data.shape[1] < 2:
            raise ValueError("Fewer than two symbols had price history.")
        st.session_state["apl_returns"] = data
        st.session_state["apl_weights"] = {n: holdings[n] for n in data.columns}
        st.session_state["apl_tickers"] = {n: ticker_by_name[n] for n in data.columns}
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

tab_frontier, tab_bl, tab_tail, tab_mc, tab_stress, tab_cvar = st.tabs(
    [
        "Efficient frontier",
        "Black-Litterman",
        "Tail risk",
        "Monte Carlo",
        "Stress test",
        "Min-CVaR & rebalance",
    ]
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
    views_text = st.text_area(
        "Views (optional; leave blank to see the market-implied prior)",
        "",
        placeholder=VIEWS_EXAMPLE,
        key="apl_views",
    )
    st.caption(
        "View assets use the same symbol forms as holdings. Loaded assets: "
        + ", ".join(f"`{name}`" for name in weights)
    )
    b1, b2, b3 = st.columns(3)
    risk_aversion = b1.number_input("Risk aversion", 0.5, 10.0, DEFAULT_RISK_AVERSION, 0.5)
    tau = b2.number_input("Tau (prior uncertainty)", 0.01, 0.5, DEFAULT_TAU, 0.01)
    bl_cap = b3.slider("Maximum weight per stock", 0.2, 1.0, 0.5, 0.05, key="apl_blcap")
    try:
        result = black_litterman_portfolio(
            cov,
            weights,
            parse_views(views_text, default_exchange),
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

with tab_cvar:
    k1, k2 = st.columns(2)
    level = k1.select_slider("CVaR confidence", [0.90, 0.95, 0.975, 0.99], value=0.95)
    cvar_cap = k2.slider("Maximum weight per stock", 0.2, 1.0, 0.5, 0.05, key="apl_cvarcap")
    entered = pd.Series(weights, dtype=float)
    entered = entered / entered.sum()
    try:
        cvar_weights, cvar_value = min_cvar_weights(returns, level, cvar_cap)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    compare_w = pd.DataFrame({"As entered": entered, "Min-CVaR": cvar_weights})
    v1, v2 = st.columns(2)
    current_cvar = portfolio_cvar(returns, entered, level)
    v1.metric(f"1-day CVaR {level:.1%}, as entered", f"{current_cvar:.2%}")
    v2.metric(f"1-day CVaR {level:.1%}, min-CVaR", f"{cvar_value:.2%}")
    st.dataframe(compare_w.style.format("{:.1%}"), use_container_width=True)
    st.bar_chart(compare_w)
    st.caption(
        "Minimises the average loss on the worst days directly. Fitted to this history, so "
        "expect a worse tail out of sample; it also tends to concentrate in a few calm stocks."
    )

    st.markdown("**Rebalance plan (whole shares, estimated costs)**")
    target_choice = st.radio(
        "Target weights", ["Min-CVaR", "As entered", "Equal weight"], horizontal=True
    )
    shares_text = st.text_area(
        "Shares you hold now: `SYMBOL shares` per line (leave blank if none)", "", key="apl_shares"
    )
    r1, r2, r3 = st.columns(3)
    cash = r1.number_input("Cash to invest (₹)", 0.0, value=500_000.0, step=10_000.0)
    lot = r2.number_input("Lot size", 1, 10_000, 1)
    min_trade = r3.number_input("Skip trades below (₹)", 0.0, value=2_000.0, step=500.0)
    if st.button("Plan trades", key="apl_plan"):
        try:
            held = parse_share_counts(shares_text, default_exchange, frozenset(returns.columns))
            tickers_kept = st.session_state.get("apl_tickers", {})
            prices = _last_prices(tuple(tickers_kept.items()))
            targets = {
                "Min-CVaR": cvar_weights,
                "As entered": entered,
                "Equal weight": pd.Series(1.0 / returns.shape[1], index=returns.columns),
            }[target_choice]
            plan, summary = rebalance_plan(
                held,
                prices,
                targets,
                cash=float(cash),
                lot_sizes={name: int(lot) for name in returns.columns},
                min_trade_value=float(min_trade),
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            q1, q2, q3, q4 = st.columns(4)
            q1.metric("Portfolio value", f"₹{summary['portfolio_value']:,.0f}")
            q2.metric("Turnover", f"{summary['turnover']:.0%}")
            q3.metric("Estimated costs", f"₹{summary['estimated_cost']:,.0f}")
            q4.metric("Cash left", f"₹{summary['cash_after']:,.0f}")
            shown = plan[["action", "trade_shares", "price", "trade_value", "est_cost"]].join(
                plan[["current_weight", "target_weight", "post_trade_weight"]]
            )
            st.dataframe(
                shown.style.format(
                    {
                        "price": "{:,.2f}",
                        "trade_value": "{:,.0f}",
                        "est_cost": "{:,.0f}",
                        "current_weight": "{:.1%}",
                        "target_weight": "{:.1%}",
                        "post_trade_weight": "{:.1%}",
                    }
                ),
                use_container_width=True,
            )
            st.caption(
                "Prices are the latest daily close and may be delayed. Costs use NSE delivery "
                "rates (an approximation for BSE listings). This plans trades; it never places "
                "orders."
            )
