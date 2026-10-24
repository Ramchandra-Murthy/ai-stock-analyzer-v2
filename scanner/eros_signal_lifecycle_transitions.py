"""EROS signal lifecycle transition analytics helpers."""

from __future__ import annotations

import pandas as pd

from scanner.eros_signal_lifecycle import analyze_eros_signal_lifecycle


def analyze_eros_signal_lifecycle_transitions(
    history: pd.DataFrame | None,
) -> pd.DataFrame:
    """Summarize the latest lifecycle state transition for each signal."""
    if history is None or history.empty:
        return pd.DataFrame()

    required = {"Timestamp", "Symbol", "Exchange", "Fusion Score"}
    if not required.issubset(history.columns):
        return pd.DataFrame()

    frame = history.copy()
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    frame["Fusion Score"] = pd.to_numeric(frame["Fusion Score"], errors="coerce")
    frame = frame.dropna(subset=["Timestamp", "Fusion Score"]).sort_values("Timestamp")
    if frame.empty:
        return pd.DataFrame()

    snapshots: list[pd.DataFrame] = []
    timestamps = frame["Timestamp"].drop_duplicates().tolist()
    for timestamp in timestamps:
        snapshot = analyze_eros_signal_lifecycle(frame[frame["Timestamp"] <= timestamp])
        if not snapshot.empty:
            snapshot = snapshot.assign(SnapshotTimestamp=timestamp)
            snapshots.append(snapshot)

    if not snapshots:
        return pd.DataFrame()

    states = pd.concat(snapshots, ignore_index=True).sort_values(
        ["Symbol", "Exchange", "SnapshotTimestamp"]
    )
    rows: list[dict[str, object]] = []

    for (symbol, exchange), group in states.groupby(["Symbol", "Exchange"]):
        lifecycle_values = group["Lifecycle"].astype(str).tolist()
        latest = group.iloc[-1]
        previous = group.iloc[-2] if len(group) >= 2 else None
        transition = (
            "INITIAL" if previous is None else f"{previous['Lifecycle']} → {latest['Lifecycle']}"
        )
        transitions = sum(
            current != prior
            for prior, current in zip(lifecycle_values, lifecycle_values[1:], strict=False)
        )

        rows.append(
            {
                "Symbol": symbol,
                "Exchange": exchange,
                "Timestamp": latest["SnapshotTimestamp"],
                "Lifecycle": latest["Lifecycle"],
                "Previous Lifecycle": (
                    str(previous["Lifecycle"]) if previous is not None else "NONE"
                ),
                "Lifecycle Transition": transition,
                "Lifecycle Age": len(group),
                "Transition Count": transitions,
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(
            ["Lifecycle Transition", "Transition Count", "Symbol"],
            ascending=[True, False, True],
        )
        .reset_index(drop=True)
    )
