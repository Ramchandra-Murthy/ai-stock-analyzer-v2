"""Statistical robustness checks for backtest results (research only).

* ``bootstrap_metrics``: stationary block bootstrap of daily returns -> confidence intervals
  for Sharpe, CAGR and max drawdown, and the probability the strategy loses money.
* ``probabilistic_sharpe`` / ``deflated_sharpe``: Bailey & Lopez de Prado. The deflated
  version discounts the best Sharpe found among many tried variants, which is exactly the
  overfitting that a parameter search produces.
"""

from __future__ import annotations

from math import erf, sqrt

import numpy as np
import pandas as pd

TRADING_DAYS = 252
EULER_GAMMA = 0.5772156649015329


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Inverse normal CDF (Acklam's rational approximation, |error| < 1.2e-9)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00, 3.754408661907416e00]
    lo, hi = 0.02425, 1 - 0.02425
    if p < lo:
        q = sqrt(-2 * np.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    if p > hi:
        q = sqrt(-2 * np.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
        * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    )


def _sharpe_daily(r: np.ndarray) -> float:
    sd = r.std(ddof=1)
    return float(r.mean() / sd) if sd > 1e-12 else 0.0


def _max_drawdown(r: np.ndarray) -> float:
    eq = np.cumprod(1.0 + r)
    return float((eq / np.maximum.accumulate(eq) - 1.0).min())


def stationary_bootstrap_indices(n: int, mean_block: float, rng: np.random.Generator) -> np.ndarray:
    """Politis-Romano stationary bootstrap: random block lengths (geometric, mean ``mean_block``)."""
    if mean_block < 1:
        raise ValueError("mean_block must be at least 1")
    p = 1.0 / mean_block
    idx = np.empty(n, dtype=np.int64)
    idx[0] = rng.integers(n)
    restart = rng.random(n) < p
    starts = rng.integers(n, size=n)
    for i in range(1, n):
        idx[i] = starts[i] if restart[i] else (idx[i - 1] + 1) % n
    return idx


def bootstrap_metrics(
    returns: pd.Series, *, n_boot: int = 1000, mean_block: float = 10.0, seed: int = 0
) -> dict[str, dict[str, float] | float]:
    """Percentile intervals (5/50/95) of annual Sharpe, CAGR and max drawdown."""
    r = pd.to_numeric(returns, errors="coerce").dropna().to_numpy(float)
    if len(r) < 60:
        raise ValueError("At least 60 return observations are needed.")
    if n_boot < 50:
        raise ValueError("n_boot must be at least 50")
    rng = np.random.default_rng(seed)
    sharpe, cagr, mdd = np.empty(n_boot), np.empty(n_boot), np.empty(n_boot)
    years = len(r) / TRADING_DAYS
    for b in range(n_boot):
        s = r[stationary_bootstrap_indices(len(r), mean_block, rng)]
        sharpe[b] = _sharpe_daily(s) * np.sqrt(TRADING_DAYS)
        final = float(np.prod(1.0 + s))
        cagr[b] = final ** (1.0 / years) - 1.0 if final > 0 else -1.0
        mdd[b] = _max_drawdown(s)

    def band(x: np.ndarray) -> dict[str, float]:
        lo, mid, hi = np.percentile(x, [5, 50, 95])
        return {"p5": float(lo), "median": float(mid), "p95": float(hi)}

    return {
        "sharpe": band(sharpe),
        "cagr": band(cagr),
        "max_drawdown": band(mdd),
        "prob_loss": float((cagr < 0).mean()),
    }


def probabilistic_sharpe(returns: pd.Series, benchmark_sharpe_annual: float = 0.0) -> float:
    """P(true Sharpe > benchmark) given sample length, skew and kurtosis (Bailey-Lopez de Prado)."""
    r = pd.to_numeric(returns, errors="coerce").dropna().to_numpy(float)
    n = len(r)
    if n < 30:
        raise ValueError("At least 30 return observations are needed.")
    sr = _sharpe_daily(r)
    bench = benchmark_sharpe_annual / np.sqrt(TRADING_DAYS)
    z = (r - r.mean()) / r.std(ddof=1)
    skew, kurt = float((z**3).mean()), float((z**4).mean())
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr**2
    if denom <= 0:
        return 0.0
    return _norm_cdf((sr - bench) * sqrt(n - 1) / sqrt(denom))


def expected_max_sharpe(n_trials: int, trial_sharpe_variance: float) -> float:
    """Expected best (daily) Sharpe among ``n_trials`` skill-less strategies."""
    if n_trials < 1 or trial_sharpe_variance < 0:
        raise ValueError("n_trials must be >= 1 and variance non-negative")
    if n_trials == 1:
        return 0.0
    return sqrt(trial_sharpe_variance) * (
        (1 - EULER_GAMMA) * _norm_ppf(1 - 1.0 / n_trials)
        + EULER_GAMMA * _norm_ppf(1 - 1.0 / (n_trials * np.e))
    )


def deflated_sharpe(returns: pd.Series, trial_sharpes_annual: list[float]) -> float:
    """Probability the best variant's skill is real after accounting for how many were tried.

    ``trial_sharpes_annual`` are the annual Sharpe ratios of every variant tested (including
    this one). Values near 1 are encouraging; below ~0.95 the result may be selection luck.
    """
    if not trial_sharpes_annual:
        raise ValueError("Provide the Sharpe ratios of all variants tried.")
    daily = np.asarray(trial_sharpes_annual, dtype=float) / np.sqrt(TRADING_DAYS)
    bench_daily = expected_max_sharpe(
        len(daily), float(daily.var(ddof=1)) if len(daily) > 1 else 0.0
    )
    return probabilistic_sharpe(returns, bench_daily * np.sqrt(TRADING_DAYS))
