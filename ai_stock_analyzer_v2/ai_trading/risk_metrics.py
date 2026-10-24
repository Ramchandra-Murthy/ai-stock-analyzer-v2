"""Book-aligned risk and performance metrics for EROS."""

from __future__ import annotations

import math

import pandas as pd


def annualized_volatility(
    returns: pd.Series,
    *,
    periods_per_year: float = 252.0,
) -> float:
    """Return annualized return volatility."""
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if len(clean) < 2:
        return 0.0
    return float(clean.std(ddof=1) * math.sqrt(periods_per_year))


def sharpe_ratio(
    returns: pd.Series,
    *,
    risk_free_rate: float = 0.0,
    periods_per_year: float = 252.0,
) -> float:
    """Return annualized Sharpe ratio using a constant annual risk-free rate."""
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if len(clean) < 2:
        return 0.0
    period_rf = (1.0 + risk_free_rate) ** (1.0 / periods_per_year) - 1.0
    excess = clean - period_rf
    volatility = excess.std(ddof=1)
    if math.isclose(volatility, 0.0, abs_tol=1e-12):
        return 0.0
    return float(excess.mean() / volatility * math.sqrt(periods_per_year))


def omega_ratio(
    returns: pd.Series,
    *,
    threshold: float = 0.0,
) -> float | None:
    """Return the Omega ratio at a return threshold."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty:
        return None
    excess = clean - threshold
    gains = float(excess[excess > 0.0].sum())
    losses = float(-excess[excess < 0.0].sum())
    if math.isclose(losses, 0.0, abs_tol=1e-12):
        return float("inf") if gains > 0.0 else None
    return gains / losses


def conditional_value_at_risk(
    returns: pd.Series,
    *,
    confidence: float = 0.95,
) -> float | None:
    """Return historical CVaR as a positive loss magnitude."""
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty:
        return None
    var = float(clean.quantile(1.0 - confidence))
    tail = clean[clean <= var]
    if tail.empty:
        return max(0.0, -var)
    return max(0.0, float(-tail.mean()))


def max_drawdown(returns: pd.Series) -> float:
    """Return maximum drawdown as a positive loss fraction."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty:
        return 0.0
    equity = (1.0 + clean).cumprod()
    drawdown = 1.0 - equity / equity.cummax()
    return float(drawdown.max())


def risk_performance_summary(
    returns: pd.Series,
    *,
    risk_free_rate: float = 0.0,
    periods_per_year: float = 252.0,
    cvar_confidence: float = 0.95,
) -> dict[str, float | None]:
    """Return a composite risk/performance view for a return series."""
    return {
        "annualized_volatility": annualized_volatility(returns, periods_per_year=periods_per_year),
        "sharpe_ratio": sharpe_ratio(
            returns,
            risk_free_rate=risk_free_rate,
            periods_per_year=periods_per_year,
        ),
        "omega_ratio": omega_ratio(returns),
        "conditional_value_at_risk": conditional_value_at_risk(returns, confidence=cvar_confidence),
        "max_drawdown": max_drawdown(returns),
    }
