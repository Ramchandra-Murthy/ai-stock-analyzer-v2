"""Intraday signal confluence helpers."""

from __future__ import annotations

import pandas as pd


def _threshold_signal(frame: pd.DataFrame, column: str, threshold: float) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index)

    values = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
    return values >= threshold


def compute_signal_confluence(board: pd.DataFrame | None) -> pd.DataFrame:
    """Combine intraday momentum, volume, breakout, and relative strength signals."""
    if board is None or board.empty:
        return pd.DataFrame()

    frame = board.copy()
    required = {"Symbol", "Exchange"}
    if not required.issubset(frame.columns):
        return pd.DataFrame()

    score = pd.Series(0.0, index=frame.index)
    for column, threshold, weight in [
        ("2-min change %", 0.75, 15),
        ("3-min change %", 1.0, 15),
        ("5-min change %", 1.5, 10),
        ("10-min change %", 2.0, 10),
        ("15-min change %", 2.5, 10),
        ("Volume surge x", 1.5, 15),
    ]:
        score += _threshold_signal(frame, column, threshold) * weight

    breakout = frame.get("Breakout", pd.Series("", index=frame.index)).astype(str)
    score += (breakout == "YES") * 10
    score += _threshold_signal(frame, "Relative Strength", 0) * 15

    result = frame.copy()
    result["Confluence Score"] = score.astype(float)
    result["Confluence"] = pd.cut(
        result["Confluence Score"],
        bins=[-1, 24, 49, 74, 100],
        labels=["LOW", "MODERATE", "HIGH", "VERY HIGH"],
    )
    sort_strength = pd.to_numeric(
        (
            result["Relative Strength"]
            if "Relative Strength" in result.columns
            else pd.Series(0.0, index=result.index)
        ),
        errors="coerce",
    ).fillna(0.0)
    sort_change = pd.to_numeric(
        (
            result["3-min change %"]
            if "3-min change %" in result.columns
            else pd.Series(0.0, index=result.index)
        ),
        errors="coerce",
    ).fillna(0.0)
    result = (
        result.assign(_sort_strength=sort_strength, _sort_change=sort_change)
        .sort_values(
            ["Confluence Score", "_sort_strength", "_sort_change"],
            ascending=[False, False, False],
            na_position="last",
        )
        .drop(columns=["_sort_strength", "_sort_change"])
        .reset_index(drop=True)
    )
    return result
