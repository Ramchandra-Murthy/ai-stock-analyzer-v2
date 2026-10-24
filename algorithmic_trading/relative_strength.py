"""Benchmark-relative return calculations."""

from __future__ import annotations

import pandas as pd


def relative_series(prices: pd.Series, benchmark: pd.Series) -> pd.Series:
    frame = pd.concat([prices, benchmark], axis=1).dropna()
    if frame.empty:
        return pd.Series(dtype=float, name="relative_strength")
    stock = frame.iloc[:, 0] / frame.iloc[:, 0].iloc[0]
    bench = frame.iloc[:, 1] / frame.iloc[:, 1].iloc[0]
    result = stock / bench
    result.name = "relative_strength"
    return result


def relative_return(
    prices: pd.Series,
    benchmark: pd.Series,
    periods: int = 20,
) -> float | None:
    rs = relative_series(prices, benchmark)
    if len(rs) <= periods:
        return None
    return float((rs.iloc[-1] / rs.iloc[-periods - 1] - 1.0) * 100.0)
