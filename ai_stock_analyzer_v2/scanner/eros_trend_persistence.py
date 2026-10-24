"""EROS trend persistence analytics helpers."""

from __future__ import annotations

import pandas as pd

from scanner.eros_fusion_history_analytics import prepare_eros_fusion_history


def analyze_eros_trend_persistence(history: pd.DataFrame | None) -> pd.DataFrame:
    """Measure the latest consecutive direction and recent directional consistency."""
    frame = prepare_eros_fusion_history(history)
    if frame.empty:
        return pd.DataFrame()

    frame = frame.sort_values(["Symbol", "Exchange", "Timestamp"]).copy()
    frame["Fusion Change"] = frame.groupby(["Symbol", "Exchange"])["Fusion Score"].diff()

    rows: list[dict[str, object]] = []
    for (symbol, exchange), group in frame.groupby(["Symbol", "Exchange"]):
        changes = group["Fusion Change"].dropna().tolist()
        if not changes:
            rows.append(
                {
                    "Symbol": symbol,
                    "Exchange": exchange,
                    "Timestamp": group["Timestamp"].iloc[-1],
                    "Fusion Score": float(group["Fusion Score"].iloc[-1]),
                    "Direction": "NEW",
                    "Streak": 0,
                    "Recent Changes": 0,
                    "Directional Consistency %": None,
                    "Persistence": "INSUFFICIENT DATA",
                }
            )
            continue

        direction = "RISING" if changes[-1] > 0 else "FALLING" if changes[-1] < 0 else "STABLE"
        streak = 1
        if direction != "STABLE":
            for change in reversed(changes[:-1]):
                if (change > 0 and direction == "RISING") or (
                    change < 0 and direction == "FALLING"
                ):
                    streak += 1
                else:
                    break

        recent = changes[-5:]
        directional = [change for change in recent if change != 0]
        consistency = (
            100.0
            * sum((change > 0) == (changes[-1] > 0) for change in directional)
            / len(directional)
            if directional
            else None
        )
        if direction == "STABLE":
            persistence = "STABLE"
        elif streak >= 3 and consistency is not None and consistency >= 80:
            persistence = "PERSISTENT"
        elif consistency is not None and consistency >= 60:
            persistence = "DEVELOPING"
        else:
            persistence = "FRAGILE"

        rows.append(
            {
                "Symbol": symbol,
                "Exchange": exchange,
                "Timestamp": group["Timestamp"].iloc[-1],
                "Fusion Score": float(group["Fusion Score"].iloc[-1]),
                "Direction": direction,
                "Streak": streak,
                "Recent Changes": len(recent),
                "Directional Consistency %": (
                    round(consistency, 2) if consistency is not None else None
                ),
                "Persistence": persistence,
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(
            ["Persistence", "Streak", "Fusion Score"],
            ascending=[True, False, False],
        )
        .reset_index(drop=True)
    )
