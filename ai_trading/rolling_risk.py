"""Book-aligned rolling risk diagnostics for return series."""

from __future__ import annotations

import pandas as pd

from ai_trading.risk_metrics import annualized_volatility, max_drawdown, sharpe_ratio


def rolling_risk_metrics(
    returns: pd.Series,
    *,
    window: int,
    periods_per_year: float = 252.0,
) -> pd.DataFrame:
    """Return rolling volatility, Sharpe ratio, and window drawdown."""
    if window < 2:
        raise ValueError("window must be at least 2")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")

    clean = pd.to_numeric(returns, errors="coerce").dropna().reset_index(drop=True)
    if len(clean) < window:
        raise ValueError("not enough observations for the requested window")

    rows: list[dict[str, float | int]] = []
    for end in range(window, len(clean) + 1):
        start = end - window
        sample = clean.iloc[start:end]
        rows.append(
            {
                "end": end - 1,
                "annualized_volatility": annualized_volatility(
                    sample, periods_per_year=periods_per_year
                ),
                "sharpe_ratio": sharpe_ratio(sample, periods_per_year=periods_per_year),
                "max_drawdown": max_drawdown(sample),
            }
        )

    return pd.DataFrame(rows)
