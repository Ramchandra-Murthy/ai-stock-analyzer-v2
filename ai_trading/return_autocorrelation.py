"""Return autocorrelation diagnostics for research backtests."""

from __future__ import annotations

import pandas as pd


def return_autocorrelation(
    returns: pd.Series,
    *,
    lag: int = 1,
) -> float | None:
    """Measure serial dependence in strategy returns at a selected lag."""
    if lag < 1:
        raise ValueError("lag must be at least 1")

    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if len(clean) <= lag:
        return None

    value = clean.autocorr(lag=lag)
    return float(value) if pd.notna(value) else None


def return_autocorrelation_summary(
    returns: pd.Series,
    *,
    lags: tuple[int, ...] = (1, 2, 5, 10),
) -> dict[str, float | None]:
    """Summarize serial dependence across selected return lags."""
    if not lags:
        raise ValueError("lags must contain at least one value")
    if any(lag < 1 for lag in lags):
        raise ValueError("lags must be at least 1")

    return {f"lag_{lag}": return_autocorrelation(returns, lag=lag) for lag in lags}
