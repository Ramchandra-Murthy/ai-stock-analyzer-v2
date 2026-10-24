"""Descriptive transition-matrix analytics for EROS regime history."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {"Timestamp", "Regime"}


def analyze_eros_regime_transition_matrix(
    history: pd.DataFrame | None,
) -> pd.DataFrame:
    """Summarize observed transitions between consecutive EROS regimes."""
    if history is None or history.empty:
        return pd.DataFrame()
    if not REQUIRED_COLUMNS.issubset(history.columns):
        return pd.DataFrame()

    frame = history.loc[:, ["Timestamp", "Regime"]].copy()
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    frame = frame.dropna(subset=["Timestamp"]).sort_values("Timestamp")
    frame = frame.drop_duplicates(subset=["Timestamp"], keep="last")
    if len(frame) < 2:
        return pd.DataFrame()

    frame["Regime"] = frame["Regime"].astype(str).str.strip()
    frame = frame[frame["Regime"].ne("")]
    if len(frame) < 2:
        return pd.DataFrame()

    previous = frame["Regime"].shift(1)
    transitions = pd.DataFrame(
        {
            "Previous Regime": previous,
            "Current Regime": frame["Regime"],
        }
    )
    transitions = transitions.dropna()
    transitions = transitions[transitions["Previous Regime"] != transitions["Current Regime"]]
    if transitions.empty:
        return pd.DataFrame()

    summary = (
        transitions.groupby(
            ["Previous Regime", "Current Regime"],
            as_index=False,
        )
        .size()
        .rename(columns={"size": "Transition Count"})
        .sort_values(
            ["Transition Count", "Previous Regime", "Current Regime"],
            ascending=[False, True, True],
        )
        .reset_index(drop=True)
    )
    total = int(summary["Transition Count"].sum())
    summary["Transition Share %"] = summary["Transition Count"].div(total).mul(100).round(2)
    if len(summary) > 1:
        residual = round(100.0 - float(summary["Transition Share %"].iloc[:-1].sum()), 2)
        summary.loc[summary.index[-1], "Transition Share %"] = residual
    return summary
