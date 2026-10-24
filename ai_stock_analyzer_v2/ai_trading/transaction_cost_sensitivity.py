"""Book-aligned transaction-cost sensitivity diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def transaction_cost_sensitivity(
    returns: pd.Series,
    *,
    turnover: pd.Series | None = None,
    cost_bps: tuple[float, ...] = (0.0, 5.0, 10.0, 20.0),
) -> pd.DataFrame:
    """Estimate strategy returns under alternative transaction-cost assumptions."""
    if not cost_bps:
        raise ValueError("cost_bps must contain at least one value")
    if any(not np.isfinite(float(value)) or float(value) < 0.0 for value in cost_bps):
        raise ValueError("cost_bps values must be finite and non-negative")

    clean_returns = pd.to_numeric(returns, errors="coerce").fillna(0.0)
    if turnover is None:
        clean_turnover = clean_returns.ne(0.0).astype(float)
    else:
        clean_turnover = pd.to_numeric(turnover, errors="coerce")
        if not clean_turnover.index.equals(clean_returns.index):
            clean_turnover = clean_turnover.reindex(clean_returns.index)
        if clean_turnover.isna().any() or not np.isfinite(clean_turnover).all():
            raise ValueError("turnover values must be finite and present for every return")
        if (clean_turnover < 0.0).any():
            raise ValueError("turnover values must be non-negative")

    rows: list[dict[str, float]] = []
    gross_return = float((1.0 + clean_returns).prod() - 1.0)
    total_turnover = float(clean_turnover.sum())
    for bps in cost_bps:
        rate = float(bps) / 10_000.0
        net_returns = clean_returns - clean_turnover * rate
        net_return = float((1.0 + net_returns).prod() - 1.0)
        rows.append(
            {
                "cost_bps": float(bps),
                "gross_return": gross_return,
                "net_return": net_return,
                "cost_drag": gross_return - net_return,
                "total_turnover": total_turnover,
            }
        )
    return pd.DataFrame(rows)


def transaction_cost_summary(
    returns: pd.Series,
    *,
    turnover: pd.Series | None = None,
    cost_bps: tuple[float, ...] = (0.0, 5.0, 10.0, 20.0),
) -> dict[str, float | None]:
    """Return base-case and most conservative cost-adjusted outcomes."""
    report = transaction_cost_sensitivity(
        returns,
        turnover=turnover,
        cost_bps=cost_bps,
    )
    if report.empty:
        return {
            "gross_return": None,
            "best_net_return": None,
            "worst_net_return": None,
            "worst_cost_bps": None,
        }

    return {
        "gross_return": float(report["gross_return"].iloc[0]),
        "best_net_return": float(report["net_return"].max()),
        "worst_net_return": float(report["net_return"].min()),
        "worst_cost_bps": float(report.loc[report["net_return"].idxmin(), "cost_bps"]),
    }
