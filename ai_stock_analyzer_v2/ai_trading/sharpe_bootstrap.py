"""Bootstrap confidence diagnostics for strategy Sharpe ratios."""

from __future__ import annotations

import pandas as pd

from ai_trading.risk_metrics import sharpe_ratio


def sharpe_bootstrap(
    returns: pd.Series,
    *,
    samples: int = 1000,
    confidence: float = 0.95,
    risk_free_rate: float = 0.0,
    periods_per_year: float = 252.0,
    seed: int = 42,
) -> dict[str, float | int | None]:
    """Estimate a bootstrap confidence interval for the annualized Sharpe ratio."""
    if samples < 1:
        raise ValueError("samples must be at least 1")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")

    values = pd.to_numeric(returns, errors="coerce").dropna().reset_index(drop=True)
    if values.empty:
        return {"observations": 0, "sharpe": None, "lower": None, "upper": None}

    observed = sharpe_ratio(
        values,
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
    )
    bootstrap = [
        sharpe_ratio(
            values.sample(n=len(values), replace=True, random_state=seed + i),
            risk_free_rate=risk_free_rate,
            periods_per_year=periods_per_year,
        )
        for i in range(samples)
    ]
    lower_quantile = (1.0 - confidence) / 2.0
    upper_quantile = 1.0 - lower_quantile
    interval = pd.Series(bootstrap).quantile([lower_quantile, upper_quantile])

    return {
        "observations": int(len(values)),
        "sharpe": float(observed),
        "lower": float(interval.iloc[0]),
        "upper": float(interval.iloc[1]),
    }
