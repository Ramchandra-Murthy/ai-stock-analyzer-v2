"""Bootstrap confidence diagnostics for realized trade expectancy."""

from __future__ import annotations

import pandas as pd

from algorithmic_trading.edge_engine import calculate_edge


def expectancy_bootstrap(
    returns: pd.Series,
    *,
    samples: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> dict[str, float | int | None]:
    """Estimate a bootstrap confidence interval for arithmetic expectancy."""
    if samples < 1:
        raise ValueError("samples must be at least 1")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")

    values = pd.to_numeric(returns, errors="coerce").dropna().reset_index(drop=True)
    if values.empty:
        return {
            "trades": 0,
            "expectancy": None,
            "lower": None,
            "upper": None,
        }

    expectancy = calculate_edge(values).expectancy
    bootstrap = [
        calculate_edge(values.sample(n=len(values), replace=True, random_state=seed + i)).expectancy
        for i in range(samples)
    ]
    lower_quantile = (1.0 - confidence) / 2.0
    upper_quantile = 1.0 - lower_quantile
    interval = pd.Series(bootstrap).quantile([lower_quantile, upper_quantile])

    return {
        "trades": int(len(values)),
        "expectancy": float(expectancy),
        "lower": float(interval.iloc[0]),
        "upper": float(interval.iloc[1]),
    }
