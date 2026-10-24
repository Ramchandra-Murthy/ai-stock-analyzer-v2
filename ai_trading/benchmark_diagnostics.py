"""Benchmark-relative performance diagnostics for research backtests."""

from __future__ import annotations

import math

import pandas as pd


def benchmark_relative_diagnostics(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
    *,
    periods_per_year: int = 252,
) -> dict[str, float | int | None]:
    """Measure active return risk and benchmark-relative efficiency."""
    if periods_per_year < 1:
        raise ValueError("periods_per_year must be at least 1")
    frame = pd.concat([strategy_returns, benchmark_returns], axis=1)
    frame = frame.apply(pd.to_numeric, errors="coerce").dropna()
    if frame.empty:
        return {
            "observations": 0,
            "active_return": None,
            "tracking_error": None,
            "information_ratio": None,
        }
    active = frame.iloc[:, 0] - frame.iloc[:, 1]
    active_return = float((1.0 + frame.iloc[:, 0]).prod() - (1.0 + frame.iloc[:, 1]).prod())
    tracking_error = (
        float(active.std(ddof=1) * math.sqrt(periods_per_year)) if len(active) > 1 else 0.0
    )
    information_ratio = (
        float(active.mean() * periods_per_year / tracking_error) if tracking_error > 0.0 else None
    )
    return {
        "observations": int(len(frame)),
        "active_return": active_return,
        "tracking_error": tracking_error,
        "information_ratio": information_ratio,
    }
