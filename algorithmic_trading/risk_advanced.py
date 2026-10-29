"""Advanced portfolio risk: tail-aware VaR, Monte Carlo paths, stress tests (research only).

Complements :mod:`algorithmic_trading.risk_metrics` (historical VaR/CVaR, drawdowns). Equity
returns are skewed and fat-tailed, so a normal VaR understates risk; Cornish-Fisher adjusts
for skew and kurtosis, and a block bootstrap keeps volatility clustering in simulated paths.
None of this predicts the future: it re-weights the past.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import kurtosis, norm, skew

from algorithmic_trading.risk_metrics import (
    TRADING_DAYS,
    drawdown_series,
    historical_cvar,
    historical_var,
    normalise_weights,
    portfolio_returns,
)

DEFAULT_MARKET_SHOCKS: dict[str, float] = {
    "Mild correction (-5%)": -0.05,
    "Correction (-10%)": -0.10,
    "Bear leg (-20%)": -0.20,
    "Crash (-30%)": -0.30,
}


def _clean(returns: pd.Series, minimum: int = 20) -> pd.Series:
    values = returns.dropna()
    if len(values) < minimum:
        raise ValueError(f"At least {minimum} return observations are needed.")
    return values


def _check_level(level: float) -> None:
    if not 0.5 < level < 1:
        raise ValueError("level must be between 0.5 and 1")


def parametric_var(returns: pd.Series, level: float = 0.95) -> float:
    """Normal-distribution VaR as a positive loss fraction."""
    _check_level(level)
    values = _clean(returns)
    z = float(norm.ppf(1.0 - level))
    return max(0.0, float(-(values.mean() + z * values.std(ddof=1))))


def cornish_fisher_var(returns: pd.Series, level: float = 0.95) -> float:
    """VaR with the Cornish-Fisher expansion for skewness and excess kurtosis."""
    _check_level(level)
    values = _clean(returns, 60)
    z = float(norm.ppf(1.0 - level))
    s = float(skew(values, bias=False))
    k = float(kurtosis(values, fisher=True, bias=False))
    z_cf = z + (z**2 - 1) * s / 6 + (z**3 - 3 * z) * k / 24 - (2 * z**3 - 5 * z) * s**2 / 36
    return max(0.0, float(-(values.mean() + z_cf * values.std(ddof=1))))


def worst_windows(returns: pd.Series, window: int = 5, count: int = 3) -> pd.Series:
    """The ``count`` worst non-overlapping ``window``-day compounded returns, worst first."""
    if window < 1 or count < 1:
        raise ValueError("window and count must be at least 1.")
    values = _clean(returns, window + 1).fillna(0.0)
    rolled = (1.0 + values).rolling(window).apply(np.prod, raw=True) - 1.0
    ordered = rolled.dropna().sort_values()
    positions = {ts: i for i, ts in enumerate(values.index)}
    chosen: list = []
    for ts in ordered.index:
        if all(abs(positions[ts] - positions[other]) >= window for other in chosen):
            chosen.append(ts)
            if len(chosen) == count:
                break
    return ordered.loc[chosen]


def tail_risk_report(returns: pd.Series) -> dict[str, float]:
    """Side-by-side VaR methods plus the shape statistics that explain their gap."""
    values = _clean(returns, 60)
    return {
        "var_95_historical": historical_var(values, 0.95),
        "var_95_parametric": parametric_var(values, 0.95),
        "var_95_cornish_fisher": cornish_fisher_var(values, 0.95),
        "var_99_historical": historical_var(values, 0.99),
        "var_99_parametric": parametric_var(values, 0.99),
        "var_99_cornish_fisher": cornish_fisher_var(values, 0.99),
        "cvar_95": historical_cvar(values, 0.95),
        "cvar_99": historical_cvar(values, 0.99),
        "skewness": float(skew(values, bias=False)),
        "excess_kurtosis": float(kurtosis(values, fisher=True, bias=False)),
        "worst_day": float(values.min()),
    }


def monte_carlo_paths(
    returns: pd.Series,
    *,
    horizon: int = TRADING_DAYS,
    n_paths: int = 2000,
    block: int = 5,
    seed: int | None = None,
) -> np.ndarray:
    """Circular block-bootstrap wealth paths, shape ``(n_paths, horizon + 1)``, starting at 1.

    Resampling blocks of consecutive days keeps short-run autocorrelation and volatility
    clustering that a day-by-day bootstrap would destroy.
    """
    if horizon < 1 or n_paths < 1 or block < 1:
        raise ValueError("horizon, n_paths and block must be at least 1.")
    values = _clean(returns, 60).to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    n_blocks = -(-horizon // block)
    starts = rng.integers(0, len(values), size=(n_paths, n_blocks))
    index = (starts[:, :, None] + np.arange(block)) % len(values)
    sampled = values[index.reshape(n_paths, -1)[:, :horizon]]
    wealth = np.cumprod(1.0 + sampled, axis=1)
    return np.hstack([np.ones((n_paths, 1)), wealth])


def summarise_paths(paths: np.ndarray, drawdown_limit: float = 0.20) -> dict[str, float]:
    """Terminal-wealth percentiles, loss probability and drawdown statistics for ``paths``."""
    if paths.ndim != 2 or paths.shape[1] < 2:
        raise ValueError("paths must be a 2-D array with at least two columns.")
    if not 0 < drawdown_limit < 1:
        raise ValueError("drawdown_limit must be in (0, 1).")
    terminal = paths[:, -1]
    drawdowns = (paths / np.maximum.accumulate(paths, axis=1) - 1.0).min(axis=1)
    p5, p25, p50, p75, p95 = np.percentile(terminal, [5, 25, 50, 75, 95])
    return {
        "terminal_p5": float(p5),
        "terminal_p25": float(p25),
        "terminal_median": float(p50),
        "terminal_p75": float(p75),
        "terminal_p95": float(p95),
        "probability_of_loss": float((terminal < 1.0).mean()),
        "median_max_drawdown": float(np.median(drawdowns)),
        "worst_max_drawdown": float(drawdowns.min()),
        "probability_drawdown_beyond_limit": float((drawdowns <= -drawdown_limit).mean()),
    }


def path_quantiles(
    paths: np.ndarray, quantiles: tuple[float, ...] = (0.05, 0.5, 0.95)
) -> pd.DataFrame:
    """Per-day wealth quantiles, ready to plot as a fan chart."""
    if not quantiles or any(not 0 <= q <= 1 for q in quantiles):
        raise ValueError("quantiles must be between 0 and 1.")
    values = np.quantile(paths, quantiles, axis=0).T
    return pd.DataFrame(values, columns=[f"p{round(q * 100)}" for q in quantiles])


def asset_betas(returns: pd.DataFrame) -> pd.Series:
    """Each asset's beta to the equal-weight basket of the same assets."""
    clean = returns.dropna()
    if clean.shape[0] < 30 or clean.shape[1] < 2:
        raise ValueError("Need at least 30 rows and 2 assets with complete data.")
    basket = clean.mean(axis=1)
    variance = float(basket.var(ddof=1))
    if variance <= 0:
        raise ValueError("The equal-weight basket has no variance.")
    return clean.apply(lambda column: float(column.cov(basket)) / variance)


def stress_test(
    returns: pd.DataFrame,
    weights: dict[str, float] | pd.Series,
    shocks: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Beta-scaled market-shock scenarios.

    Each row is a scenario, each column an asset's contribution (weight x beta x shock), and
    ``portfolio`` is their sum. Betas are measured against the equal-weight basket of every
    column in ``returns`` (the universe), so the portfolio may hold a subset of it. The result
    is a rough, linear estimate: in real crashes correlations rise and losses usually
    exceed it.
    """
    w = normalise_weights(weights)
    scenarios = DEFAULT_MARKET_SHOCKS if shocks is None else shocks
    if not scenarios:
        raise ValueError("At least one scenario is required.")
    missing = [s for s in w.index if s not in returns.columns]
    if missing:
        raise ValueError(f"No return data for: {', '.join(missing)}")
    betas = asset_betas(returns).reindex(w.index)
    table = pd.DataFrame(
        {name: w * betas * shock for name, shock in scenarios.items()},
    ).T
    table["portfolio"] = table.sum(axis=1)
    return table


def custom_stress(weights: dict[str, float] | pd.Series, asset_shocks: dict[str, float]) -> float:
    """Portfolio return if each named asset moves by its shock (others unchanged)."""
    w = normalise_weights(weights)
    unknown = [s for s in asset_shocks if s not in w.index]
    if unknown:
        raise ValueError(f"Shocks refer to assets not in the portfolio: {', '.join(unknown)}")
    return float(sum(w[s] * shock for s, shock in asset_shocks.items()))


def diversification_ratio(returns: pd.DataFrame, weights: dict[str, float] | pd.Series) -> float:
    """Weighted average asset volatility over portfolio volatility (1 = no diversification)."""
    w = normalise_weights(weights)
    sub = returns[list(w.index)].dropna()
    if sub.shape[0] < 30:
        raise ValueError("Need at least 30 complete rows.")
    cov = sub.cov().to_numpy()
    portfolio_vol = float(np.sqrt(w.to_numpy() @ cov @ w.to_numpy()))
    if portfolio_vol <= 1e-12:
        raise ValueError("Portfolio volatility is zero.")
    return float(w.to_numpy() @ np.sqrt(np.diag(cov)) / portfolio_vol)


def average_pairwise_correlation(returns: pd.DataFrame) -> float:
    """Mean of the off-diagonal correlations (needs at least two assets)."""
    corr = returns.dropna().corr().to_numpy()
    if corr.shape[0] < 2:
        raise ValueError("Need at least two assets.")
    off_diagonal = corr[~np.eye(corr.shape[0], dtype=bool)]
    return float(off_diagonal.mean())


def advanced_risk_summary(
    returns: pd.DataFrame, weights: dict[str, float] | pd.Series
) -> dict[str, float]:
    """One-call summary used by the Streamlit page and handy in notebooks."""
    port = portfolio_returns(returns, weights)
    summary = tail_risk_report(port)
    summary["max_drawdown"] = float(drawdown_series(port).min())
    summary["diversification_ratio"] = diversification_ratio(returns, weights)
    return summary
