"""Reusable VWAP and opening-range calculations for intraday analysis."""

# fmt: off

from __future__ import annotations

from typing import Any

import pandas as pd


def vwap_orb_metrics(
    frame: pd.DataFrame,
    orb_minutes: tuple[int, ...] = (5, 15),
) -> dict[str, Any]:
    """Return session VWAP and configurable opening-range reference metrics."""
    if frame is None or frame.empty:
        return {}

    data = frame.copy()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    required = {"High", "Low", "Close", "Volume"}
    if not required.issubset(data.columns):
        return {}

    data = data.dropna(subset=list(required)).sort_index()
    if data.empty:
        return {}

    session_date = data.index[-1].date()
    session = data[list(data.columns)].loc[
        [stamp.date() == session_date for stamp in data.index]
    ]
    high = pd.to_numeric(session["High"], errors="coerce")
    low = pd.to_numeric(session["Low"], errors="coerce")
    close = pd.to_numeric(session["Close"], errors="coerce")
    volume = pd.to_numeric(session["Volume"], errors="coerce")
    typical = (high + low + close) / 3.0
    volume_total = volume.sum()
    vwap = float((typical * volume).sum() / volume_total) if volume_total > 0 else float("nan")
    latest_close = float(close.iloc[-1])
    result: dict[str, Any] = {
        "VWAP": round(vwap, 2) if pd.notna(vwap) else None,
        "VWAP distance %": (
            round((latest_close - vwap) / vwap * 100.0, 2)
            if pd.notna(vwap) and vwap != 0
            else None
        ),
        "VWAP bias": (
            "ABOVE" if latest_close > vwap else "BELOW" if latest_close < vwap else "AT"
        )
        if pd.notna(vwap)
        else "UNKNOWN",
    }

    interval_minutes = _interval_minutes(session.index)
    for minutes in orb_minutes:
        if minutes < 1:
            continue
        bars = max(1, int(minutes / interval_minutes)) if interval_minutes else 1
        opening = session.head(bars)
        if opening.empty:
            continue
        orb_high = float(pd.to_numeric(opening["High"], errors="coerce").max())
        orb_low = float(pd.to_numeric(opening["Low"], errors="coerce").min())
        result[f"ORB {minutes}m high"] = round(orb_high, 2)
        result[f"ORB {minutes}m low"] = round(orb_low, 2)
        result[f"ORB {minutes}m range %"] = (
            round((orb_high - orb_low) / orb_low * 100.0, 2) if orb_low > 0 else None
        )
        result[f"ORB {minutes}m state"] = (
            "ABOVE"
            if latest_close > orb_high
            else "BELOW"
            if latest_close < orb_low
            else "INSIDE"
        )
    return result


def _interval_minutes(index: pd.Index) -> int:
    """Estimate the source candle interval in whole minutes."""
    if len(index) < 2:
        return 1
    deltas = pd.Series(index).sort_values().diff().dropna().dt.total_seconds() / 60.0
    positive = deltas[deltas > 0]
    if positive.empty:
        return 1
    return max(1, int(round(float(positive.median()))))

# fmt: on
