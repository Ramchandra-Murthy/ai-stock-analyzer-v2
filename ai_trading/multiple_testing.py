"""Book-aligned multiple-testing diagnostic for strategy Sharpe ratios."""

from __future__ import annotations

import math

import pandas as pd


def sharpe_ratio_haircut(
    sharpe_ratios: pd.Series,
    *,
    trials: int,
) -> float | None:
    """Return the best Sharpe ratio adjusted for multiple strategy trials."""
    if trials < 1:
        raise ValueError("trials must be at least 1")

    clean = pd.to_numeric(sharpe_ratios, errors="coerce").dropna()
    if clean.empty:
        return None

    best = float(clean.max())
    if trials == 1:
        return best

    return float(best - math.sqrt(2.0 * math.log(trials)))


def multiple_testing_summary(
    sharpe_ratios: pd.Series,
    *,
    trials: int,
) -> dict[str, float | None]:
    """Summarize best and multiple-testing-adjusted Sharpe ratios."""
    clean = pd.to_numeric(sharpe_ratios, errors="coerce").dropna()
    adjusted = sharpe_ratio_haircut(clean, trials=trials)

    return {
        "configurations": float(len(clean)),
        "best_sharpe": float(clean.max()) if not clean.empty else None,
        "adjusted_sharpe": adjusted,
    }
