"""Price-jump session history analytics helpers."""

from __future__ import annotations

import pandas as pd


def summarize_price_jump_history(
    history: pd.DataFrame | None,
) -> pd.DataFrame:
    """Summarize repeated price-jump observations by symbol and exchange."""
    if history is None or history.empty:
        return pd.DataFrame()

    required = {"Timestamp", "Symbol", "Exchange"}
    if not required.issubset(history.columns):
        return pd.DataFrame()

    change_columns = [
        column for column in history.columns if str(column).startswith("Change over ")
    ]
    if not change_columns:
        return pd.DataFrame()

    frame = history.copy()
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    change_column = change_columns[0]
    frame[change_column] = pd.to_numeric(frame[change_column], errors="coerce")
    frame = frame.dropna(subset=["Timestamp", change_column])
    if frame.empty:
        return pd.DataFrame()

    summary = (
        frame.groupby(["Symbol", "Exchange"], as_index=False)
        .agg(
            Observations=("Symbol", "size"),
            Average_Change=(change_column, "mean"),
            Peak_Change=(change_column, "max"),
            First_Seen=("Timestamp", "min"),
            Last_Seen=("Timestamp", "max"),
        )
        .sort_values(
            ["Observations", "Average_Change", "Peak_Change"],
            ascending=[False, False, False],
        )
        .reset_index(drop=True)
    )
    summary["Persistence"] = pd.cut(
        summary["Observations"],
        bins=[0, 1, 2, 4, float("inf")],
        labels=["ONE", "REPEATED", "PERSISTENT", "HIGH PERSISTENCE"],
    )
    return summary
