"""Helpers for descriptive intraday setup session-phase analysis."""

from __future__ import annotations

from typing import Any

import pandas as pd


def session_phase(value: Any) -> str:
    """Classify an observation timestamp into a regular-session phase."""
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("Asia/Kolkata")
    else:
        timestamp = timestamp.tz_convert("Asia/Kolkata")

    minutes = timestamp.hour * 60 + timestamp.minute
    if minutes < 600:
        return "Opening (09:15-10:00)"
    if minutes < 720:
        return "Morning (10:00-12:00)"
    if minutes < 840:
        return "Midday (12:00-14:00)"
    return "Closing (14:00-15:30)"


def regime_statistics(
    outcomes: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Summarize observed setup outcomes by session phase and state."""
    columns = [
        "Session phase",
        "State",
        "Setups",
        "Positive outcomes",
        "Negative outcomes",
        "Positive rate %",
        "Average change %",
    ]
    if not outcomes:
        return pd.DataFrame(columns=columns)

    frame = pd.DataFrame(list(outcomes.values()))
    required = {"State", "Price change %", "First observed"}
    if not required.issubset(frame.columns):
        return pd.DataFrame(columns=columns)

    frame["Price change %"] = pd.to_numeric(frame["Price change %"], errors="coerce")
    frame["First observed"] = pd.to_datetime(frame["First observed"], errors="coerce")
    frame = frame.dropna(subset=["State", "Price change %", "First observed"])
    if frame.empty:
        return pd.DataFrame(columns=columns)

    frame["Session phase"] = frame["First observed"].map(session_phase)
    grouped = frame.groupby(["Session phase", "State"])["Price change %"]
    stats = grouped.agg(
        Setups="count",
        **{"Average change %": "mean"},
    ).reset_index()
    stats["Positive outcomes"] = grouped.apply(lambda values: int((values > 0).sum())).values
    stats["Negative outcomes"] = grouped.apply(lambda values: int((values < 0).sum())).values
    stats["Positive rate %"] = stats["Positive outcomes"] / stats["Setups"] * 100
    stats[["Positive rate %", "Average change %"]] = stats[
        ["Positive rate %", "Average change %"]
    ].round(2)

    phase_order = {
        "Opening (09:15-10:00)": 0,
        "Morning (10:00-12:00)": 1,
        "Midday (12:00-14:00)": 2,
        "Closing (14:00-15:30)": 3,
    }
    stats["_phase_order"] = stats["Session phase"].map(phase_order)
    return (
        stats.sort_values(["_phase_order", "Setups"], ascending=[True, False])
        .drop(columns="_phase_order")
        .reset_index(drop=True)[columns]
    )
