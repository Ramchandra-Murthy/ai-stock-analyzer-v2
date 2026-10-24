"""Portfolio risk measures from historical returns (research only)."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def normalise_weights(weights: dict[str, float] | pd.Series) -> pd.Series:
    w = pd.Series(weights, dtype=float)
    if w.empty or (w < 0).any() or not np.isfinite(w).all() or w.sum() <= 0:
        raise ValueError("Weights must be non-negative, finite and sum to more than zero.")
    return w / w.sum()


def portfolio_returns(returns: pd.DataFrame, weights: dict[str, float] | pd.Series) -> pd.Series:
    """Daily returns of a constant-weight (daily rebalanced) portfolio."""
    w = normalise_weights(weights)
    missing = [c for c in w.index if c not in returns.columns]
    if missing:
        raise ValueError(f"No return data for: {', '.join(missing)}")
    return returns[list(w.index)].fillna(0.0).mul(w, axis=1).sum(axis=1)


def historical_var(returns: pd.Series, level: float = 0.95) -> float:
    """Loss (positive number) not exceeded on ``level`` of days."""
    if not 0.5 < level < 1:
        raise ValueError("level must be between 0.5 and 1")
    values = returns.dropna()
    if len(values) < 20:
        raise ValueError("At least 20 return observations are needed.")
    return float(-np.quantile(values, 1 - level))


def historical_cvar(returns: pd.Series, level: float = 0.95) -> float:
    """Average loss on the days at or beyond the VaR threshold (expected shortfall)."""
    values = returns.dropna()
    var = -historical_var(values, level)
    tail = values[values <= var]
    return float(-tail.mean())


def risk_contributions(returns: pd.DataFrame, weights: dict[str, float] | pd.Series) -> pd.Series:
    """Share of portfolio variance contributed by each holding (sums to 1)."""
    w = normalise_weights(weights)
    cov = returns[list(w.index)].cov()
    marginal = cov @ w
    total = float(w @ marginal)
    if total <= 0:
        return pd.Series(0.0, index=w.index)
    return w * marginal / total


def drawdown_series(returns: pd.Series) -> pd.Series:
    equity = (1.0 + returns.fillna(0.0)).cumprod()
    return equity / equity.cummax() - 1.0


def breaker_simulation(returns: pd.Series, limit: float = 0.10, cooldown: int = 21) -> pd.DataFrame:
    """Go to cash for ``cooldown`` days after drawdown from the peak breaches ``limit``.

    The decision at bar t uses the drawdown through t and applies from t+1. After the
    cooldown the peak resets so the rule does not lock itself out forever.
    """
    if not 0 < limit < 1 or cooldown < 1:
        raise ValueError("limit must be in (0, 1) and cooldown at least 1")
    out = np.zeros(len(returns))
    equity = peak = 1.0
    off_until = -1
    flat_until_applies = False
    for t, r in enumerate(returns.fillna(0.0).to_numpy()):
        exposed = t > off_until
        out[t] = r if exposed else 0.0
        equity *= 1.0 + out[t]
        peak = max(peak, equity)
        if exposed and equity / peak - 1.0 <= -limit:
            off_until = t + cooldown
            peak = equity  # reset after the cooldown starts
            flat_until_applies = True
    frame = pd.DataFrame({"raw": returns.fillna(0.0), "with_breaker": out}, index=returns.index)
    frame.attrs["triggered"] = flat_until_applies
    return frame


def risk_summary(returns: pd.DataFrame, weights: dict[str, float] | pd.Series) -> dict[str, float]:
    port = portfolio_returns(returns, weights)
    return {
        "annual_return": float(port.mean() * TRADING_DAYS),
        "annual_volatility": float(port.std(ddof=1) * np.sqrt(TRADING_DAYS)),
        "var_95": historical_var(port, 0.95),
        "cvar_95": historical_cvar(port, 0.95),
        "var_99": historical_var(port, 0.99),
        "cvar_99": historical_cvar(port, 0.99),
        "max_drawdown": float(drawdown_series(port).min()),
    }
