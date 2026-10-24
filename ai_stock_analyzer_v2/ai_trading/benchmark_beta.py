"""Benchmark beta diagnostics for research backtests."""

from __future__ import annotations

import math

import pandas as pd


def benchmark_beta(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> float | None:
    """Estimate strategy beta relative to benchmark returns."""
    frame = pd.concat([strategy_returns, benchmark_returns], axis=1)
    frame = frame.apply(pd.to_numeric, errors="coerce").dropna()
    if len(frame) < 2:
        return None

    benchmark_variance = float(frame.iloc[:, 1].var(ddof=1))
    if math.isclose(benchmark_variance, 0.0, abs_tol=1e-12):
        return None

    covariance = float(frame.iloc[:, 0].cov(frame.iloc[:, 1]))
    return covariance / benchmark_variance


def benchmark_beta_summary(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> dict[str, float | int | None]:
    """Summarize benchmark beta and aligned observations."""
    frame = pd.concat([strategy_returns, benchmark_returns], axis=1)
    frame = frame.apply(pd.to_numeric, errors="coerce").dropna()
    return {
        "observations": int(len(frame)),
        "beta": benchmark_beta(strategy_returns, benchmark_returns),
    }
