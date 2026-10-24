"""Price-jump and intraday confluence integration helpers."""

from __future__ import annotations

import pandas as pd


def match_price_jumps_to_confluence(
    jumps: pd.DataFrame | None,
    board: pd.DataFrame | None,
    min_score: float = 75.0,
) -> pd.DataFrame:
    """Attach current confluence metrics to price-jump scan results."""
    if jumps is None or jumps.empty or board is None or board.empty:
        return pd.DataFrame()

    required_jumps = {"Symbol", "Exchange"}
    required_board = {"Symbol", "Exchange", "Confluence Score", "Confluence"}
    if not required_jumps.issubset(jumps.columns) or not required_board.issubset(board.columns):
        return pd.DataFrame()

    metrics = board[
        [
            column
            for column in [
                "Symbol",
                "Exchange",
                "Confluence Score",
                "Confluence",
                "Relative Strength",
                "Volume surge x",
                "Breakout",
            ]
            if column in board.columns
        ]
    ].copy()
    metrics = metrics.drop_duplicates(["Symbol", "Exchange"], keep="last")

    result = jumps.merge(metrics, on=["Symbol", "Exchange"], how="inner")
    if result.empty:
        return result

    result["Confluence Score"] = pd.to_numeric(result["Confluence Score"], errors="coerce")
    result["Confluence Confirmation"] = result["Confluence Score"] >= min_score
    result = result.sort_values(
        ["Confluence Confirmation", "Confluence Score"],
        ascending=[False, False],
        na_position="last",
    ).reset_index(drop=True)
    return result
