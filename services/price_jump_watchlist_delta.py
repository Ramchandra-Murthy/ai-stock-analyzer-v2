"""Descriptive changes between consecutive price-jump watchlists."""

from __future__ import annotations

from typing import Any

import pandas as pd

STATUS_COLUMNS = ["Status", "Rank change", "Symbol", "Exchange", "Change %", "Day %", "RVOL"]


def compare_watchlists(
    previous: pd.DataFrame | None,
    current: pd.DataFrame | None,
) -> pd.DataFrame:
    """Describe new, dropped, promoted and demoted watchlist symbols."""
    if previous is None:
        return pd.DataFrame(columns=STATUS_COLUMNS)

    previous = _normalise(previous)
    current = _normalise(current)

    previous_ranks = {
        row["Symbol"]: int(row["Rank"]) for row in previous.to_dict("records") if row["Symbol"]
    }
    current_ranks = {
        row["Symbol"]: int(row["Rank"]) for row in current.to_dict("records") if row["Symbol"]
    }

    rows: list[dict[str, Any]] = []
    for row in current.to_dict("records"):
        symbol = row["Symbol"]
        if symbol not in previous_ranks:
            status = "NEW"
            rank_change = None
        else:
            rank_change = previous_ranks[symbol] - row["Rank"]
            if rank_change > 0:
                status = "UP"
            elif rank_change < 0:
                status = "DOWN"
            else:
                status = "UNCHANGED"
        rows.append(
            {
                "Status": status,
                "Rank change": rank_change,
                "Symbol": symbol,
                "Exchange": row["Exchange"],
                "Change %": row["Change %"],
                "Day %": row["Day %"],
                "RVOL": row["RVOL"],
            }
        )

    for row in previous.to_dict("records"):
        symbol = row["Symbol"]
        if symbol not in current_ranks:
            rows.append(
                {
                    "Status": "DROPPED",
                    "Rank change": None,
                    "Symbol": symbol,
                    "Exchange": row["Exchange"],
                    "Change %": row["Change %"],
                    "Day %": row["Day %"],
                    "RVOL": row["RVOL"],
                }
            )

    if not rows:
        return pd.DataFrame(columns=STATUS_COLUMNS)

    order = {"NEW": 0, "UP": 1, "DOWN": 2, "UNCHANGED": 3, "DROPPED": 4}
    frame = pd.DataFrame(rows, columns=STATUS_COLUMNS)
    frame["_order"] = frame["Status"].map(order)
    return (
        frame.sort_values(
            ["_order", "Rank change"],
            ascending=[True, False],
            na_position="last",
        )
        .drop(columns="_order")
        .reset_index(drop=True)
    )


def _normalise(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["Rank", *STATUS_COLUMNS[2:]])

    result = frame.copy()
    if "Rank" not in result.columns:
        result.insert(0, "Rank", range(1, len(result) + 1))

    result["Symbol"] = result.get("Symbol", "").fillna("").astype(str)
    result["Exchange"] = result.get("Exchange", "—").fillna("—").astype(str)
    change_columns = [column for column in result.columns if column.startswith("Change over ")]
    result["Change %"] = (
        pd.to_numeric(result[change_columns[0]], errors="coerce") if change_columns else pd.NA
    )
    for column in ["Day %", "RVOL"]:
        if column not in result.columns:
            result[column] = pd.NA
    return result[["Rank", "Symbol", "Exchange", "Change %", "Day %", "RVOL"]]
