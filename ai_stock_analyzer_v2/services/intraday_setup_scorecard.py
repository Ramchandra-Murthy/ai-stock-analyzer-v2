"""Descriptive intraday setup scorecard from observed scanner fields."""

# fmt: off

from __future__ import annotations

import pandas as pd

SCORE_COMPONENTS = (
    ("Trend", 20.0),
    ("Volume", 20.0),
    ("VWAP", 15.0),
    ("Momentum", 15.0),
    ("Breakout", 15.0),
    ("Session", 15.0),
)


def build_setup_scorecard(row: dict) -> dict[str, float]:
    """Convert observed setup evidence into a transparent 0-100 score."""
    values = {
        "Trend": _signal(row.get("Trend")),
        "Volume": _signal(row.get("Volume surge x"), threshold=1.5),
        "VWAP": _vwap_signal(row),
        "Momentum": _signal(row.get("5-min change %"), threshold=0.5),
        "Breakout": _breakout_signal(row),
        "Session": _session_signal(row),
    }
    return {
        component: round(values[component] * weight, 1)
        for component, weight in SCORE_COMPONENTS
    } | {"Total": round(sum(values[c] * w for c, w in SCORE_COMPONENTS), 1)}


def scorecard_frame(frame: pd.DataFrame | None) -> pd.DataFrame:
    """Add transparent component scores and total score to a scan dataframe."""
    if frame is None or frame.empty:
        return pd.DataFrame()
    result = frame.copy()
    scores = pd.DataFrame(
        [build_setup_scorecard(row) for row in result.to_dict(orient="records")],
        index=result.index,
    )
    for column in scores.columns:
        result[f"Setup {column}"] = scores[column]
    return result


def _signal(value: object, threshold: float = 1.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.5 if str(value).strip() else 0.0
    if numeric >= threshold:
        return 1.0
    if numeric <= 0:
        return 0.0
    return 0.5


def _vwap_signal(row: dict) -> float:
    bias = str(row.get("VWAP bias", "")).upper()
    if bias in {"ABOVE", "BELOW"}:
        return 1.0
    return 0.5 if row.get("VWAP") else 0.0


def _breakout_signal(row: dict) -> float:
    states = {str(row.get(f"ORB {minutes}m state", "")).upper() for minutes in (5, 15)}
    if states & {"ABOVE", "BELOW"}:
        return 1.0
    return 0.5 if "INSIDE" in states else 0.0


def _session_signal(row: dict) -> float:
    phase = str(row.get("Session phase", "")).upper()
    return 1.0 if phase in {"OPEN", "MIDDAY", "CLOSE"} else 0.5
# fmt: on
