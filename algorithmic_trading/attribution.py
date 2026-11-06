"""Performance attribution: factor regression, rolling risk-adjusted metrics, contributions.

Research only. A regression of portfolio returns on market (and other) factor returns splits
what came from taking market risk (beta) from what is left over (alpha). With a short history
the alpha estimate is very noisy, so the t-statistic is reported next to it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _naive(obj: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    """Drop any timezone so tz-aware factors (Yahoo) align with tz-naive returns."""
    if getattr(obj.index, "tz", None) is not None:
        obj = obj.copy()
        obj.index = obj.index.tz_localize(None)
    obj.index = pd.DatetimeIndex(obj.index).normalize()
    return obj


@dataclass(frozen=True)
class FactorFit:
    alpha_annual: float
    alpha_t: float
    betas: pd.Series
    beta_t: pd.Series
    r_squared: float
    observations: int
    residual_vol_annual: float


def factor_regression(
    returns: pd.Series,
    factors: pd.DataFrame,
    *,
    risk_free_annual: float = 0.0,
    min_obs: int = 60,
) -> FactorFit:
    """OLS of excess portfolio returns on excess factor returns (all daily)."""
    if factors.shape[1] < 1:
        raise ValueError("At least one factor is required.")
    joined = pd.concat([_naive(returns).rename("y"), _naive(factors)], axis=1, join="inner")
    joined = joined.replace([np.inf, -np.inf], np.nan).dropna()
    if len(joined) < min_obs:
        raise ValueError(f"Only {len(joined)} overlapping days; at least {min_obs} are needed.")
    rf = risk_free_annual / TRADING_DAYS
    y = joined["y"].to_numpy() - rf
    x = np.column_stack([np.ones(len(joined)), joined.drop(columns="y").to_numpy() - rf])
    if np.linalg.matrix_rank(x) < x.shape[1]:
        raise ValueError("Factors are collinear or constant; remove a duplicate factor.")
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    resid = y - x @ coef
    dof = len(y) - x.shape[1]
    sigma2 = float(resid @ resid) / dof
    se = np.sqrt(np.diag(sigma2 * np.linalg.inv(x.T @ x)))
    t = coef / se
    ss_tot = float(((y - y.mean()) ** 2).sum())
    names = list(joined.columns[1:])
    return FactorFit(
        alpha_annual=float(coef[0] * TRADING_DAYS),
        alpha_t=float(t[0]),
        betas=pd.Series(coef[1:], index=names),
        beta_t=pd.Series(t[1:], index=names),
        r_squared=float(1.0 - float(resid @ resid) / ss_tot) if ss_tot > 0 else 0.0,
        observations=len(y),
        residual_vol_annual=float(np.sqrt(sigma2) * np.sqrt(TRADING_DAYS)),
    )


def rolling_sharpe(
    returns: pd.Series, window: int = 63, risk_free_annual: float = 0.0
) -> pd.Series:
    """Annualised Sharpe ratio over a trailing window (NaN until the window fills)."""
    if window < 20:
        raise ValueError("window must be at least 20 days.")
    excess = returns - risk_free_annual / TRADING_DAYS
    mean = excess.rolling(window).mean()
    std = excess.rolling(window).std(ddof=1)
    return (mean / std.where(std > 1e-12) * np.sqrt(TRADING_DAYS)).rename("rolling_sharpe")


def rolling_max_drawdown(returns: pd.Series, window: int = 126) -> pd.Series:
    """Worst peak-to-trough fall inside each trailing window (a negative number)."""
    if window < 20:
        raise ValueError("window must be at least 20 days.")

    def worst(chunk: np.ndarray) -> float:
        wealth = np.cumprod(1.0 + chunk)
        return float((wealth / np.maximum.accumulate(wealth) - 1.0).min())

    return returns.rolling(window).apply(worst, raw=True).rename("rolling_max_drawdown")


def return_contributions(returns: pd.DataFrame, weights: dict[str, float] | pd.Series) -> pd.Series:
    """Each asset's share of total return for daily-rebalanced fixed weights.

    Contribution is the sum over days of ``weight * asset return``; the values add up to the
    sum of the portfolio's daily returns, and ``share`` columns are not needed to see who drove it.
    """
    w = pd.Series(weights, dtype=float)
    if (w < 0).any() or w.sum() <= 0:
        raise ValueError("weights must be non-negative and not all zero.")
    w = w / w.sum()
    missing = [s for s in w.index if s not in returns.columns]
    if missing:
        raise ValueError(f"No return data for: {', '.join(missing)}")
    clean = returns[list(w.index)].dropna()
    if clean.empty:
        raise ValueError("No overlapping return history.")
    return (clean * w).sum().sort_values(ascending=False).rename("contribution")
