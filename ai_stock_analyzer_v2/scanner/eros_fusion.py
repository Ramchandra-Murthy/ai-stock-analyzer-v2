"""Transparent EROS fusion scoring helpers."""

from __future__ import annotations

import pandas as pd


def _persistence_score(observations: float) -> float:
    return min(100.0, max(0.0, float(observations) / 5.0 * 100.0))


def compute_eros_fusion(
    confluence: pd.DataFrame | None,
    confluence_history: pd.DataFrame | None = None,
    price_jumps: pd.DataFrame | None = None,
    institutional_momentum: dict[str, object] | None = None,
    price_jump_history: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Combine available stock-level and market-context screening signals."""
    if confluence is None or confluence.empty:
        return pd.DataFrame()

    required = {"Symbol", "Exchange", "Confluence Score"}
    if not required.issubset(confluence.columns):
        return pd.DataFrame()

    result = confluence.copy()
    result["Confluence Score"] = pd.to_numeric(result["Confluence Score"], errors="coerce")
    result = result.dropna(subset=["Confluence Score"])
    if result.empty:
        return pd.DataFrame()

    result["Confluence Component"] = result["Confluence Score"].clip(0, 100)

    persistence = {}
    if confluence_history is not None and not confluence_history.empty:
        required_history = {"Symbol", "Exchange", "Timestamp"}
        if required_history.issubset(confluence_history.columns):
            counts = confluence_history.groupby(["Symbol", "Exchange"]).size().to_dict()
            persistence = {
                (symbol, exchange): _persistence_score(count)
                for (symbol, exchange), count in counts.items()
            }

    result["Persistence Component"] = [
        persistence.get((symbol, exchange), 0.0)
        for symbol, exchange in zip(result["Symbol"], result["Exchange"], strict=True)
    ]

    jump_keys = set()
    if price_jumps is not None and not price_jumps.empty:
        if {"Symbol", "Exchange"}.issubset(price_jumps.columns):
            jump_keys = set(zip(price_jumps["Symbol"], price_jumps["Exchange"], strict=True))
    jump_persistence = {}
    if price_jump_history is not None and not price_jump_history.empty:
        required_jump_history = {"Symbol", "Exchange", "Timestamp"}
        if required_jump_history.issubset(price_jump_history.columns):
            counts = price_jump_history.groupby(["Symbol", "Exchange"]).size().to_dict()
            jump_persistence = {
                (symbol, exchange): _persistence_score(count)
                for (symbol, exchange), count in counts.items()
            }

    result["Price Jump Component"] = [
        jump_persistence.get(
            (symbol, exchange),
            (
                0.0
                if price_jump_history is not None
                else 100.0 if (symbol, exchange) in jump_keys else 0.0
            ),
        )
        for symbol, exchange in zip(
            result["Symbol"],
            result["Exchange"],
            strict=True,
        )
    ]

    institutional_score = None
    if institutional_momentum:
        raw_score = institutional_momentum.get("score")
        if raw_score is not None:
            try:
                institutional_score = float(raw_score)
            except (TypeError, ValueError):
                institutional_score = None

    components = ["Confluence Component", "Persistence Component"]
    weights = {
        "Confluence Component": 50.0,
        "Persistence Component": 20.0,
        "Price Jump Component": 15.0,
        "Institutional Component": 15.0,
    }
    result["Institutional Component"] = (
        institutional_score if institutional_score is not None else 50.0
    )

    active_weights = components + ["Price Jump Component"]
    if institutional_score is not None:
        active_weights.append("Institutional Component")
    weight_total = sum(weights[column] for column in active_weights)
    result["Fusion Score"] = (
        sum(result[column] * weights[column] for column in active_weights) / weight_total
    )
    result["Fusion Score"] = result["Fusion Score"].clip(0, 100).round(2)
    result["Fusion Coverage"] = len(active_weights)

    display_columns = [
        "Symbol",
        "Exchange",
        "Fusion Score",
        "Fusion Coverage",
        "Confluence Component",
        "Persistence Component",
        "Price Jump Component",
        "Institutional Component",
    ]
    extras = [
        column
        for column in ["Sector", "Price", "Confluence", "Relative Strength"]
        if column in result.columns
    ]
    return (
        result[display_columns[:2] + extras + display_columns[2:]]
        .sort_values(
            ["Fusion Score", "Confluence Component"],
            ascending=[False, False],
        )
        .reset_index(drop=True)
    )
