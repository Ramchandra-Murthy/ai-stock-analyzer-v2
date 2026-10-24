"""Trade-duration diagnostics for research backtests."""

from __future__ import annotations

import pandas as pd


def trade_duration_summary(
    durations: pd.Series,
) -> dict[str, float | int | None]:
    """Summarize realized trade holding durations."""
    clean = pd.to_numeric(durations, errors="coerce").dropna()
    if (clean < 0.0).any():
        raise ValueError("durations must be non-negative")
    if clean.empty:
        return {
            "trades": 0,
            "mean": None,
            "median": None,
            "minimum": None,
            "maximum": None,
            "p25": None,
            "p75": None,
        }

    quantiles = clean.quantile([0.25, 0.75])
    return {
        "trades": int(len(clean)),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "minimum": float(clean.min()),
        "maximum": float(clean.max()),
        "p25": float(quantiles.loc[0.25]),
        "p75": float(quantiles.loc[0.75]),
    }
