"""EROS multi-window trend analytics helpers."""

# Ruff's I001 is explicitly skipped for this manually ordered import block.
# ruff: isort: skip_file

from __future__ import annotations

import pandas as pd

from scanner.eros_fusion_history_analytics import prepare_eros_fusion_history

WINDOWS = (2, 3, 5)


def analyze_eros_multi_window_trend(history: pd.DataFrame | None) -> pd.DataFrame:
    """Compare recent EROS fusion changes across observation windows."""
    frame = prepare_eros_fusion_history(history)
    if frame.empty:
        return pd.DataFrame()

    frame = frame.sort_values(["Symbol", "Exchange", "Timestamp"]).reset_index(drop=True)
    grouped = frame.groupby(["Symbol", "Exchange"], group_keys=False)

    rows: list[dict[str, object]] = []
    for (symbol, exchange), group in grouped:
        scores = group["Fusion Score"].reset_index(drop=True)
        if scores.empty:
            continue

        row: dict[str, object] = {
            "Symbol": symbol,
            "Exchange": exchange,
            "Timestamp": group["Timestamp"].iloc[-1],
            "Fusion Score": float(scores.iloc[-1]),
        }
        changes: list[float] = []
        for window in WINDOWS:
            if len(scores) > window:
                change = float(scores.iloc[-1] - scores.iloc[-1 - window])
            else:
                change = None

            row[f"{window}-observation Change"] = change
            if change is not None:
                changes.append(change)

        if changes:
            if all(change > 0 for change in changes):
                alignment = "RISING"
            elif all(change < 0 for change in changes):
                alignment = "FALLING"
            else:
                alignment = "MIXED"

            row["Window Alignment"] = alignment
            row["Strongest Window Change"] = max(changes, key=abs)
        else:
            row["Window Alignment"] = "INSUFFICIENT DATA"
            row["Strongest Window Change"] = None

        rows.append(row)

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)
    return result.sort_values(
        ["Window Alignment", "Fusion Score"],
        ascending=[True, False],
    ).reset_index(drop=True)
