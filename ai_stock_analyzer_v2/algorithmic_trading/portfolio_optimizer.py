"""Long-only portfolio construction: min-variance, max-Sharpe, risk parity and HRP.

Inputs are daily returns. Covariance is Ledoit-Wolf shrunk by default because sample
covariance of many assets is noisy and makes optimisers chase estimation error. Optimised
weights are in-sample estimates, not promises; test them walk-forward before trusting them.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import leaves_list, linkage
from scipy.optimize import minimize
from scipy.spatial.distance import squareform
from sklearn.covariance import LedoitWolf

TRADING_DAYS = 252
METHODS = (
    "Equal weight",
    "Minimum variance",
    "Maximum Sharpe",
    "Risk parity",
    "Hierarchical risk parity",
)


def covariance(returns: pd.DataFrame, shrink: bool = True) -> pd.DataFrame:
    clean = returns.dropna()
    if clean.shape[0] < 60 or clean.shape[1] < 2:
        raise ValueError("Need at least 60 rows and 2 assets with complete data.")
    values = LedoitWolf().fit(clean.to_numpy()).covariance_ if shrink else clean.cov().to_numpy()
    return pd.DataFrame(values * TRADING_DAYS, index=clean.columns, columns=clean.columns)


def _check_cap(n: int, max_weight: float) -> None:
    if not 0 < max_weight <= 1 or max_weight * n < 1 - 1e-9:
        raise ValueError("max_weight must be in (0, 1] and allow weights to sum to 1.")


def _solve(objective, n: int, max_weight: float, x0: np.ndarray | None = None) -> np.ndarray:
    _check_cap(n, max_weight)
    start = np.full(n, 1.0 / n) if x0 is None else x0
    res = minimize(
        objective,
        start,
        method="SLSQP",
        bounds=[(0.0, max_weight)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
        options={"maxiter": 500, "ftol": 1e-12},
    )
    if not res.success:
        raise ValueError(f"Optimiser did not converge: {res.message}")
    w = np.clip(res.x, 0.0, max_weight)
    return w / w.sum()


def min_variance(cov: pd.DataFrame, max_weight: float = 1.0) -> pd.Series:
    c = cov.to_numpy()
    return pd.Series(_solve(lambda w: w @ c @ w, len(c), max_weight), index=cov.index)


def max_sharpe(
    mean: pd.Series, cov: pd.DataFrame, rf: float = 0.0, max_weight: float = 1.0
) -> pd.Series:
    c, mu = cov.to_numpy(), mean.reindex(cov.index).to_numpy() - rf
    if (mu <= 0).all():
        raise ValueError("No asset has an expected return above the risk-free rate.")
    return pd.Series(
        _solve(lambda w: -(w @ mu) / np.sqrt(w @ c @ w), len(c), max_weight), index=cov.index
    )


def risk_parity(cov: pd.DataFrame) -> pd.Series:
    """Weights whose risk contributions are equal (long-only)."""
    c = cov.to_numpy()
    n = len(c)

    def objective(w: np.ndarray) -> float:
        rc = w * (c @ w)
        return float(((rc[:, None] - rc[None, :]) ** 2).sum())

    w = _solve(objective, n, 1.0)
    return pd.Series(w, index=cov.index)


def _cluster_variance(cov: np.ndarray, items: list[int]) -> float:
    sub = cov[np.ix_(items, items)]
    ivp = 1.0 / np.diag(sub)
    ivp /= ivp.sum()
    return float(ivp @ sub @ ivp)


def hrp(cov: pd.DataFrame) -> pd.Series:
    """Hierarchical risk parity (Lopez de Prado): cluster, then split risk top-down."""
    c = cov.to_numpy()
    sd = np.sqrt(np.diag(c))
    corr = np.clip(c / np.outer(sd, sd), -1.0, 1.0)
    dist = np.sqrt(0.5 * (1.0 - corr))
    np.fill_diagonal(dist, 0.0)
    order = [int(i) for i in leaves_list(linkage(squareform(dist, checks=False), "single"))]
    weights = pd.Series(1.0, index=order)
    clusters = [order]
    while clusters:
        clusters = [
            half
            for cl in clusters
            if len(cl) > 1
            for half in (cl[: len(cl) // 2], cl[len(cl) // 2 :])
        ]
        for left, right in zip(clusters[::2], clusters[1::2], strict=True):
            vl, vr = _cluster_variance(c, left), _cluster_variance(c, right)
            alpha = 1.0 - vl / (vl + vr)
            weights[left] *= alpha
            weights[right] *= 1.0 - alpha
    out = weights.sort_index()
    return pd.Series(out.to_numpy() / out.sum(), index=cov.index)


def optimise(
    returns: pd.DataFrame, method: str, *, max_weight: float = 1.0, shrink: bool = True
) -> pd.Series:
    if method not in METHODS:
        raise ValueError(f"Unknown method: {method}")
    cov = covariance(returns, shrink)
    n = len(cov)
    if method == "Equal weight":
        return pd.Series(1.0 / n, index=cov.index)
    if method == "Minimum variance":
        return min_variance(cov, max_weight)
    if method == "Maximum Sharpe":
        return max_sharpe(returns[cov.index].mean() * TRADING_DAYS, cov, 0.0, max_weight)
    if method == "Risk parity":
        return risk_parity(cov)
    return hrp(cov)


def portfolio_stats(weights: pd.Series, returns: pd.DataFrame) -> dict[str, float]:
    port = returns[weights.index].fillna(0.0) @ weights
    vol = float(port.std(ddof=1) * np.sqrt(TRADING_DAYS))
    ret = float(port.mean() * TRADING_DAYS)
    return {
        "annual_return": ret,
        "annual_volatility": vol,
        "sharpe": ret / vol if vol > 1e-12 else 0.0,
    }


def walk_forward_weights(
    returns: pd.DataFrame,
    method: str,
    *,
    train: int = 504,
    rebalance: int = 63,
    max_weight: float = 1.0,
) -> pd.Series:
    """Out-of-sample daily returns: re-optimise on the trailing ``train`` rows, hold ``rebalance`` rows."""
    if train < 120 or rebalance < 5 or len(returns) <= train + rebalance:
        raise ValueError("Not enough history for the chosen train/rebalance sizes.")
    parts = []
    for start in range(train, len(returns) - 1, rebalance):
        w = optimise(returns.iloc[start - train : start], method, max_weight=max_weight)
        block = returns.iloc[start : start + rebalance]
        parts.append(block[w.index].fillna(0.0) @ w)
    return pd.concat(parts)
