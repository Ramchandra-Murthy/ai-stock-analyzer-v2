"""Descriptive recency analytics for the current EROS regime."""

from __future__ import annotations

import pandas as pd

from scanner.eros_regime_duration import analyze_eros_regime_duration


def analyze_eros_regime_recency(
    history: pd.DataFrame | None,
) -> pd.DataFrame:
    """Describe how recently the current EROS regime began."""
    if history is None or history.empty:
        return pd.DataFrame()

    frame = history.copy()
    if not {"Timestamp", "Regime"}.issubset(frame.columns):
        return pd.DataFrame()

    frame["Regime"] = frame["Regime"].astype(str)
    frame = frame[frame["Regime"].str.strip().ne("")]
    if frame.empty:
        return pd.DataFrame()

    runs = analyze_eros_regime_duration(frame)
    if runs.empty:
        return pd.DataFrame()

    current = runs.iloc[-1]
    previous_regime = runs.iloc[-2]["Regime"] if len(runs) > 1 else "NO PRIOR REGIME"

    return pd.DataFrame(
        [
            {
                "Current Regime": current["Regime"],
                "Latest Timestamp": current["End"],
                "Current Run Start": current["Start"],
                "Current Run Snapshots": int(current["Snapshots"]),
                "Current Run Duration Minutes": float(current["Duration Minutes"]),
                "Previous Regime": previous_regime,
                "Historical Transitions": len(runs) - 1,
            }
        ]
    )
