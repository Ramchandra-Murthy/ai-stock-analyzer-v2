"""Benchmark upside and downside capture diagnostics."""

from __future__ import annotations

import math

import pandas as pd


def benchmark_capture(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> dict[str, float | int | None]:
    """Measure strategy participation in benchmark up and down periods."""
    frame = pd.concat([strategy_returns, benchmark_returns], axis=1)
    frame = frame.apply(pd.to_numeric, errors="coerce").dropna()
    if frame.empty:
        return {
            "observations": 0,
            "upside_capture": None,
            "downside_capture": None,
        }

    strategy = frame.iloc[:, 0]
    benchmark = frame.iloc[:, 1]
    up = benchmark > 0.0
    down = benchmark < 0.0

    def compounded(values: pd.Series) -> float | None:
        if values.empty:
            return None
        return float((1.0 + values).prod() - 1.0)

    benchmark_up = compounded(benchmark[up])
    strategy_up = compounded(strategy[up])
    benchmark_down = compounded(benchmark[down])
    strategy_down = compounded(strategy[down])

    upside = (
        strategy_up / benchmark_up
        if benchmark_up is not None
        and not math.isclose(benchmark_up, 0.0, abs_tol=1e-12)
        and strategy_up is not None
        else None
    )
    downside = (
        strategy_down / benchmark_down
        if benchmark_down is not None
        and not math.isclose(benchmark_down, 0.0, abs_tol=1e-12)
        and strategy_down is not None
        else None
    )

    return {
        "observations": int(len(frame)),
        "upside_capture": float(upside) if upside is not None else None,
        "downside_capture": float(downside) if downside is not None else None,
    }
