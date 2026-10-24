"""Monthly return diagnostics for research backtests."""

from __future__ import annotations

import pandas as pd


def monthly_return_diagnostics(returns: pd.Series) -> pd.DataFrame:
    """Aggregate daily returns into compounded calendar-month returns."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    columns = ["year", "month", "return"]
    if clean.empty:
        return pd.DataFrame(columns=columns)

    index = pd.to_datetime(clean.index, errors="coerce")
    if index.isna().any():
        raise ValueError("returns index must contain valid timestamps")

    frame = clean.copy()
    frame.index = index
    grouped = frame.groupby([frame.index.year, frame.index.month])
    result = grouped.apply(lambda values: float((1.0 + values).prod() - 1.0))
    result.index.names = ["year", "month"]
    return result.rename("return").reset_index()
