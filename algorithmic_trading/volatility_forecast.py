"""Volatility forecasting: EWMA, rolling and GARCH(1,1), with out-of-sample scoring.

Volatility is far more predictable than returns, which makes it useful for position sizing,
option pricing context and risk limits. All forecasts here are one-step-ahead and use data up
to and including bar *t* to forecast bar *t+1*. Values are daily standard deviations unless a
function says "annual".
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

TRADING_DAYS = 252


def ewma_variance(returns: pd.Series, lam: float = 0.94) -> pd.Series:
    """RiskMetrics EWMA conditional variance: v[t] = lam*v[t-1] + (1-lam)*r[t]^2.

    Value at t is the forecast for t+1 (it includes r[t]). The seed is the variance of the
    first 20 returns, so the first few forecasts carry a small look-ahead into those 20 bars.
    """
    if not 0 < lam < 1:
        raise ValueError("lam must be in (0, 1)")
    r = pd.to_numeric(returns, errors="coerce").dropna()
    if len(r) < 30:
        raise ValueError("At least 30 returns are needed.")
    values = r.to_numpy(float)
    fcst = np.empty(len(values))
    previous = float(np.var(values[:20], ddof=0))  # seed
    for t, value in enumerate(values):
        previous = lam * previous + (1.0 - lam) * value**2
        fcst[t] = previous
    return pd.Series(fcst, index=r.index)


def rolling_variance(returns: pd.Series, window: int = 20) -> pd.Series:
    r = pd.to_numeric(returns, errors="coerce")
    return r.pow(2).rolling(window, min_periods=window).mean()


@dataclass(frozen=True)
class GarchFit:
    omega: float
    alpha: float
    beta: float
    log_likelihood: float
    n_obs: int
    mean: float = 0.0  # in-sample mean return, used to demean forecasts causally

    @property
    def persistence(self) -> float:
        return self.alpha + self.beta

    @property
    def long_run_variance(self) -> float:
        return self.omega / (1.0 - self.persistence)

    @property
    def half_life(self) -> float:
        """Days for a variance shock to decay by half."""
        return (
            float(np.log(0.5) / np.log(self.persistence))
            if 0 < self.persistence < 1
            else float("inf")
        )


def _garch_filter(
    r: np.ndarray, omega: float, alpha: float, beta: float, seed: float | None = None
) -> np.ndarray:
    """Conditional variance h[t] for bar t (uses data up to t-1)."""
    h = np.empty(len(r))
    h[0] = r.var() if seed is None else seed
    for t in range(1, len(r)):
        h[t] = omega + alpha * r[t - 1] ** 2 + beta * h[t - 1]
    return h


def fit_garch(returns: pd.Series) -> GarchFit:
    """Gaussian maximum likelihood GARCH(1,1) on demeaned returns."""
    r = pd.to_numeric(returns, errors="coerce").dropna().to_numpy(float)
    if len(r) < 250:
        raise ValueError("At least 250 returns are needed to fit GARCH.")
    mean = float(r.mean())
    r = r - mean
    scale = r.std()
    x = r / scale  # fit on unit-scale data for numerical stability

    def nll(p: np.ndarray) -> float:
        omega, alpha, beta = p
        if omega <= 1e-9 or alpha < 0 or beta < 0 or alpha + beta >= 0.9999:
            return 1e10
        h = _garch_filter(x, omega, alpha, beta)
        return float(0.5 * np.sum(np.log(h) + x**2 / h))

    best = None
    for a0, b0 in ((0.05, 0.90), (0.10, 0.80), (0.03, 0.95)):
        res = minimize(
            nll,
            [(1 - a0 - b0), a0, b0],
            method="Nelder-Mead",
            options={"xatol": 1e-7, "fatol": 1e-9, "maxiter": 4000},
        )
        if best is None or res.fun < best.fun:
            best = res
    omega, alpha, beta = best.x
    if not (omega > 0 and alpha >= 0 and beta >= 0 and alpha + beta < 1):
        raise ValueError("GARCH fit did not converge to a stationary solution.")
    return GarchFit(
        float(omega * scale**2),
        float(alpha),
        float(beta),
        float(-best.fun - 0.5 * len(x) * np.log(2 * np.pi)),
        len(x),
    )


def garch_forecast_series(returns: pd.Series, fit: GarchFit) -> pd.Series:
    """One-step-ahead variance forecast: value at t forecasts t+1 and uses r[t] and earlier."""
    r = pd.to_numeric(returns, errors="coerce").dropna()
    x = r.to_numpy(float) - fit.mean  # fitted mean and long-run seed: nothing from later bars
    h = _garch_filter(x, fit.omega, fit.alpha, fit.beta, seed=fit.long_run_variance)
    nxt = fit.omega + fit.alpha * x**2 + fit.beta * h
    return pd.Series(nxt, index=r.index)


def garch_term_structure(
    fit: GarchFit, last_variance_forecast: float, horizon: int = 30
) -> np.ndarray:
    """Forecast daily variance for steps 1..horizon, decaying to the long-run level."""
    k = np.arange(horizon)
    return fit.long_run_variance + fit.persistence**k * (
        last_variance_forecast - fit.long_run_variance
    )


def qlike(forecast_var: pd.Series, realised_sq: pd.Series) -> float:
    """QLIKE loss (lower is better); robust ranking of variance forecasts."""
    both = pd.concat([forecast_var, realised_sq], axis=1).dropna()
    both = both[both.iloc[:, 0] > 0]
    f, y = both.iloc[:, 0], both.iloc[:, 1].clip(lower=1e-12)
    return float((np.log(f) + y / f).mean())


def compare_forecasters(
    returns: pd.Series, *, refit_every: int = 126, min_train: int = 750
) -> pd.DataFrame:
    """Out-of-sample QLIKE for rolling, EWMA and GARCH (GARCH refit on a growing window)."""
    r = pd.to_numeric(returns, errors="coerce").dropna()
    if len(r) < min_train + 126:
        raise ValueError("Not enough history for an out-of-sample comparison.")
    realised = r.pow(2).shift(-1)  # what the forecast at t is trying to predict
    ewma = ewma_variance(r)
    roll = rolling_variance(r, 20)
    garch = pd.Series(np.nan, index=r.index)
    for start in range(min_train, len(r) - 1, refit_every):
        fit = fit_garch(r.iloc[:start])
        block = garch_forecast_series(r.iloc[: min(start + refit_every, len(r))], fit)
        garch.iloc[start : start + refit_every] = block.iloc[start : start + refit_every].to_numpy()
    mask = garch.notna()
    rows = {
        "Rolling 20d": qlike(roll[mask], realised[mask]),
        "EWMA 0.94": qlike(ewma[mask], realised[mask]),
        "GARCH(1,1)": qlike(garch[mask], realised[mask]),
    }
    return pd.DataFrame({"QLIKE (lower is better)": rows}).sort_values("QLIKE (lower is better)")


def annualised_volatility(daily_variance: float) -> float:
    return float(np.sqrt(max(daily_variance, 0.0) * TRADING_DAYS))
