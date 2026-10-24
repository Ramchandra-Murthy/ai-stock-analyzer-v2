"""Fundamental intelligence features for AI equity research."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class FundamentalSnapshot:
    """Normalized fundamental metrics for one equity."""

    revenue_growth_pct: float | None
    earnings_growth_pct: float | None
    profit_margin_pct: float | None
    debt_to_equity: float | None
    return_on_equity_pct: float | None
    pe_ratio: float | None


METRIC_COLUMNS = [
    "revenue_growth_pct",
    "earnings_growth_pct",
    "profit_margin_pct",
    "debt_to_equity",
    "return_on_equity_pct",
    "pe_ratio",
]


def _number(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_fundamentals(data: dict[str, object]) -> FundamentalSnapshot:
    """Normalize raw fundamental values into stable percentage/ratio fields."""
    return FundamentalSnapshot(
        revenue_growth_pct=_number(data.get("revenue_growth_pct")),
        earnings_growth_pct=_number(data.get("earnings_growth_pct")),
        profit_margin_pct=_number(data.get("profit_margin_pct")),
        debt_to_equity=_number(data.get("debt_to_equity")),
        return_on_equity_pct=_number(data.get("return_on_equity_pct")),
        pe_ratio=_number(data.get("pe_ratio")),
    )


def fundamentals_frame(
    snapshots: dict[str, FundamentalSnapshot],
) -> pd.DataFrame:
    """Build a symbol-indexed table from normalized fundamental snapshots."""
    rows = []
    for symbol, snapshot in snapshots.items():
        row = {"symbol": str(symbol).upper()}
        row.update({column: getattr(snapshot, column) for column in METRIC_COLUMNS})
        rows.append(row)
    if not rows:
        return pd.DataFrame(columns=["symbol", *METRIC_COLUMNS])
    return pd.DataFrame(rows, columns=["symbol", *METRIC_COLUMNS])


def fundamental_quality_score(snapshot: FundamentalSnapshot) -> float:
    """Create a transparent 0-100 research quality score from available metrics."""
    components: list[float] = []

    if snapshot.revenue_growth_pct is not None:
        components.append(max(0.0, min(100.0, 50.0 + snapshot.revenue_growth_pct)))
    if snapshot.earnings_growth_pct is not None:
        components.append(max(0.0, min(100.0, 50.0 + snapshot.earnings_growth_pct)))
    if snapshot.profit_margin_pct is not None:
        components.append(max(0.0, min(100.0, snapshot.profit_margin_pct * 2.0)))
    if snapshot.return_on_equity_pct is not None:
        components.append(max(0.0, min(100.0, snapshot.return_on_equity_pct * 2.0)))
    if snapshot.debt_to_equity is not None:
        components.append(max(0.0, min(100.0, 100.0 - snapshot.debt_to_equity * 25.0)))
    if snapshot.pe_ratio is not None:
        components.append(max(0.0, min(100.0, 100.0 - max(snapshot.pe_ratio - 10.0, 0.0) * 2.0)))

    return round(sum(components) / len(components), 1) if components else 0.0
