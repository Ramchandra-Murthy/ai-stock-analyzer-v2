"""Advanced portfolio construction: efficient frontier and Black-Litterman (research only).

Builds on :mod:`algorithmic_trading.portfolio_optimizer` (same long-only weights, same
annualised covariance). Everything here is an in-sample estimate: expected returns are the
noisiest input in portfolio theory, which is why Black-Litterman anchors on market-implied
returns and only tilts them toward explicit, confidence-weighted views.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from algorithmic_trading.portfolio_optimizer import _check_cap, max_sharpe, min_variance

DEFAULT_RISK_AVERSION = 2.5
DEFAULT_TAU = 0.05


def _max_return(mu: np.ndarray, max_weight: float) -> float:
    """Highest expected return reachable long-only with a per-asset cap (greedy fill)."""
    remaining, total = 1.0, 0.0
    for value in np.sort(mu)[::-1]:
        take = min(max_weight, remaining)
        total += take * value
        remaining -= take
        if remaining <= 1e-12:
            break
    return float(total)


def _min_variance_at_return(
    c: np.ndarray, mu: np.ndarray, target: float, max_weight: float, x0: np.ndarray
) -> np.ndarray | None:
    n = len(c)
    res = minimize(
        lambda w: w @ c @ w,
        x0,
        jac=lambda w: 2.0 * c @ w,
        method="SLSQP",
        bounds=[(0.0, max_weight)] * n,
        constraints=[
            {"type": "eq", "fun": lambda w: w.sum() - 1.0},
            {"type": "eq", "fun": lambda w: w @ mu - target},
        ],
        options={"maxiter": 500, "ftol": 1e-12},
    )
    if not res.success:
        return None
    w = np.clip(res.x, 0.0, max_weight)
    return np.asarray(w / w.sum(), dtype=float)


def efficient_frontier(
    mean: pd.Series,
    cov: pd.DataFrame,
    *,
    n_points: int = 25,
    max_weight: float = 1.0,
    rf: float = 0.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Long-only efficient frontier from the minimum-variance portfolio to the highest return.

    ``mean`` and ``cov`` must both be annualised. Returns ``(points, weights)``: ``points``
    has ``return``, ``volatility`` and ``sharpe`` per frontier point, and ``weights`` has the
    matching portfolio weights (one row per point, one column per asset). Points the solver
    cannot reach are skipped rather than approximated.
    """
    if n_points < 3:
        raise ValueError("n_points must be at least 3.")
    n = len(cov)
    _check_cap(n, max_weight)
    mu = mean.reindex(cov.index).to_numpy(dtype=float)
    if not np.isfinite(mu).all():
        raise ValueError("Expected returns are missing for some assets in the covariance matrix.")
    c = cov.to_numpy(dtype=float)
    start = min_variance(cov, max_weight).to_numpy()
    low, high = float(start @ mu), _max_return(mu, max_weight)
    if high - low < 1e-9:
        raise ValueError("Expected returns are too similar to build a frontier.")
    rows: list[dict[str, float]] = []
    kept: list[np.ndarray] = []
    x0 = start
    for target in np.linspace(low, high, n_points):
        w = _min_variance_at_return(c, mu, float(target), max_weight, x0)
        if w is None:
            continue
        x0 = w
        vol = float(np.sqrt(w @ c @ w))
        ret = float(w @ mu)
        rows.append(
            {"return": ret, "volatility": vol, "sharpe": (ret - rf) / vol if vol > 1e-12 else 0.0}
        )
        kept.append(w)
    if len(rows) < 3:
        raise ValueError("The optimiser could only solve a few frontier points; widen max_weight.")
    return pd.DataFrame(rows), pd.DataFrame(kept, columns=cov.index)


@dataclass(frozen=True)
class View:
    """One investor view.

    ``weights`` maps symbols to +1 / -1 style coefficients: ``{"TCS": 1}`` is an absolute view
    ("TCS returns ``expected_return``"), ``{"TCS": 1, "INFY": -1}`` is relative ("TCS beats
    INFY by ``expected_return``"). ``expected_return`` is annual. ``confidence`` is strictly
    between 0 and 1; higher values pull the posterior closer to the view.
    """

    weights: dict[str, float]
    expected_return: float
    confidence: float = 0.5


def implied_returns(
    cov: pd.DataFrame,
    market_weights: dict[str, float] | pd.Series,
    risk_aversion: float = DEFAULT_RISK_AVERSION,
) -> pd.Series:
    """Equilibrium returns implied by market weights: ``pi = risk_aversion * cov @ w``."""
    if risk_aversion <= 0:
        raise ValueError("risk_aversion must be positive.")
    w = pd.Series(market_weights, dtype=float).reindex(cov.index)
    if w.isna().any() or (w < 0).any() or w.sum() <= 0:
        raise ValueError("Market weights must be non-negative and cover every asset.")
    w = w / w.sum()
    return pd.Series(risk_aversion * cov.to_numpy() @ w.to_numpy(), index=cov.index)


def _pick_matrix(views: list[View], index: pd.Index) -> tuple[np.ndarray, np.ndarray]:
    p = np.zeros((len(views), len(index)))
    q = np.zeros(len(views))
    for i, view in enumerate(views):
        if not 0 < view.confidence < 1:
            raise ValueError("View confidence must be strictly between 0 and 1.")
        if not view.weights:
            raise ValueError("Every view needs at least one asset.")
        unknown = [s for s in view.weights if s not in index]
        if unknown:
            raise ValueError(f"View refers to unknown assets: {', '.join(unknown)}")
        for symbol, coefficient in view.weights.items():
            p[i, index.get_loc(symbol)] = coefficient
        q[i] = view.expected_return
    return p, q


def black_litterman_returns(
    cov: pd.DataFrame,
    market_weights: dict[str, float] | pd.Series,
    views: list[View],
    *,
    tau: float = DEFAULT_TAU,
    risk_aversion: float = DEFAULT_RISK_AVERSION,
) -> pd.Series:
    """Posterior expected returns after blending market-implied returns with ``views``.

    The view uncertainty of each view is ``tau * p' cov p * (1 - c) / c`` where ``c`` is its
    confidence, so a 50% confidence view is as uncertain as the prior on that combination.
    """
    prior = implied_returns(cov, market_weights, risk_aversion)
    if not views:
        return prior
    if tau <= 0:
        raise ValueError("tau must be positive.")
    c = cov.to_numpy(dtype=float)
    p, q = _pick_matrix(views, cov.index)
    omega = np.diag(
        [
            (1.0 - v.confidence) / v.confidence * tau * float(p[i] @ c @ p[i])
            for i, v in enumerate(views)
        ]
    )
    pi = prior.to_numpy()
    middle = p @ (tau * c) @ p.T + omega
    adjustment = tau * c @ p.T @ np.linalg.solve(middle, q - p @ pi)
    return pd.Series(pi + adjustment, index=cov.index)


def black_litterman_portfolio(
    cov: pd.DataFrame,
    market_weights: dict[str, float] | pd.Series,
    views: list[View],
    *,
    tau: float = DEFAULT_TAU,
    risk_aversion: float = DEFAULT_RISK_AVERSION,
    max_weight: float = 1.0,
) -> dict[str, pd.Series]:
    """Prior returns, posterior returns and the long-only max-Sharpe weights on the posterior."""
    prior = implied_returns(cov, market_weights, risk_aversion)
    posterior = black_litterman_returns(
        cov, market_weights, views, tau=tau, risk_aversion=risk_aversion
    )
    weights = max_sharpe(posterior, cov, 0.0, max_weight)
    return {"prior": prior, "posterior": posterior, "weights": weights}
