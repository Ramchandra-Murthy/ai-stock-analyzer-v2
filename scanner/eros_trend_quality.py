"""EROS trend quality analytics helpers."""

from __future__ import annotations

import pandas as pd

from scanner.eros_fusion_history_analytics import prepare_eros_fusion_history


def analyze_eros_trend_quality(history: pd.DataFrame | None) -> pd.DataFrame:
    """Measure directional consistency and movement efficiency of EROS trends."""
    frame = prepare_eros_fusion_history(history)
    if frame.empty:
        return pd.DataFrame()

    frame = frame.sort_values(["Symbol", "Exchange", "Timestamp"]).copy()
    frame["Fusion Change"] = frame.groupby(["Symbol", "Exchange"])["Fusion Score"].diff()

    rows: list[dict[str, object]] = []
    for (symbol, exchange), group in frame.groupby(["Symbol", "Exchange"]):
        changes = group["Fusion Change"].dropna().tail(5).tolist()
        if not changes:
            rows.append(
                {
                    "Symbol": symbol,
                    "Exchange": exchange,
                    "Timestamp": group["Timestamp"].iloc[-1],
                    "Fusion Score": float(group["Fusion Score"].iloc[-1]),
                    "Direction": "NEW",
                    "Net Change": 0.0,
                    "Average Change": None,
                    "Directional Consistency %": None,
                    "Trend Efficiency %": None,
                    "Trend Quality": "INSUFFICIENT DATA",
                }
            )
            continue

        direction = "RISING" if changes[-1] > 0 else "FALLING" if changes[-1] < 0 else "STABLE"
        non_zero = [change for change in changes if change != 0]
        consistency = (
            100.0 * sum((change > 0) == (changes[-1] > 0) for change in non_zero) / len(non_zero)
            if non_zero
            else None
        )
        net_change = float(sum(changes))
        gross_change = float(sum(abs(change) for change in changes))
        efficiency = 100.0 * abs(net_change) / gross_change if gross_change else None
        average_change = float(sum(changes) / len(changes))

        if direction == "STABLE":
            quality = "STABLE"
        elif (
            consistency is not None
            and efficiency is not None
            and consistency >= 80
            and efficiency >= 70
        ):
            quality = "COHERENT"
        elif consistency is not None and consistency >= 60:
            quality = "DEVELOPING"
        else:
            quality = "MIXED"

        rows.append(
            {
                "Symbol": symbol,
                "Exchange": exchange,
                "Timestamp": group["Timestamp"].iloc[-1],
                "Fusion Score": float(group["Fusion Score"].iloc[-1]),
                "Direction": direction,
                "Net Change": round(net_change, 2),
                "Average Change": round(average_change, 2),
                "Directional Consistency %": (
                    round(consistency, 2) if consistency is not None else None
                ),
                "Trend Efficiency %": (round(efficiency, 2) if efficiency is not None else None),
                "Trend Quality": quality,
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(
            ["Trend Quality", "Directional Consistency %", "Fusion Score"],
            ascending=[True, False, False],
            na_position="last",
        )
        .reset_index(drop=True)
    )
