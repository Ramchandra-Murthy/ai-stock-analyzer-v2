"""Helpers for summarizing observed intraday setup outcomes."""

from __future__ import annotations

from typing import Any

import pandas as pd


def setup_statistics(outcomes: dict[str, dict[str, Any]]) -> pd.DataFrame:
    """Summarize observed outcomes by setup state."""
    columns = [
        "State",
        "Setups",
        "Positive outcomes",
        "Negative outcomes",
        "Flat outcomes",
        "Positive rate %",
        "Average change %",
        "Best change %",
        "Worst change %",
    ]
    if not outcomes:
        return pd.DataFrame(columns=columns)

    frame = pd.DataFrame(list(outcomes.values()))
    required = {"State", "Price change %"}
    if not required.issubset(frame.columns):
        return pd.DataFrame(columns=columns)

    frame["Price change %"] = pd.to_numeric(frame["Price change %"], errors="coerce")
    frame = frame.dropna(subset=["State", "Price change %"])
    if frame.empty:
        return pd.DataFrame(columns=columns)

    grouped = frame.groupby("State")["Price change %"]
    stats = grouped.agg(
        Setups="count",
        **{
            "Average change %": "mean",
            "Best change %": "max",
            "Worst change %": "min",
        },
    ).reset_index()
    stats["Positive outcomes"] = grouped.apply(lambda values: int((values > 0).sum())).values
    stats["Negative outcomes"] = grouped.apply(lambda values: int((values < 0).sum())).values
    stats["Flat outcomes"] = grouped.apply(lambda values: int((values == 0).sum())).values
    stats["Positive rate %"] = stats["Positive outcomes"] / stats["Setups"] * 100
    numeric = [
        "Positive rate %",
        "Average change %",
        "Best change %",
        "Worst change %",
    ]
    stats[numeric] = stats[numeric].round(2)
    return stats[columns].sort_values("Setups", ascending=False).reset_index(drop=True)
