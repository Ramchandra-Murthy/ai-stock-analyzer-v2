"""Cost-adjusted evaluation of completed directional AI signal outcomes.

This is a per-trade research estimate, not a portfolio backtest. It assumes
one entry and one exit at the recorded prices, applies the selected India
equity cost model to both sides, and does not model fills, market impact,
position overlap, capital constraints or taxes beyond the configured model.
"""

from __future__ import annotations

import math

import pandas as pd

from algorithmic_trading.trading_costs import IndiaEquityCostModel, round_trip_bps

GROUP_COLUMNS = ["signal", "horizon_days", "exchange"]
EVALUATION_COLUMNS = [
    "timestamp",
    "symbol",
    *GROUP_COLUMNS,
    "gross_return_pct",
    "estimated_cost_pct",
    "net_return_pct",
    "benchmark_return_pct",
    "directional_benchmark_return_pct",
    "excess_return_pct",
    "evaluated",
]


def evaluate_signal_trades(
    history: pd.DataFrame,
    cost_model: IndiaEquityCostModel,
) -> pd.DataFrame:
    """Apply estimated round-trip costs to completed LONG/SHORT signal returns.

    return_pct must already be direction-adjusted (positive is favourable for
    either LONG or SHORT). If benchmark_return_pct is present, it is interpreted
    as the underlying benchmark's buy-and-hold return over the identical
    observation window; it is direction-adjusted before comparison.
    """
    if history.empty:
        return pd.DataFrame(columns=EVALUATION_COLUMNS)
    required = {"completed", "return_pct", *GROUP_COLUMNS, "symbol"}
    missing = required.difference(history.columns)
    if missing:
        raise ValueError(f"Signal history is missing required columns: {', '.join(sorted(missing))}")

    rows = history.copy()
    rows["return_pct"] = pd.to_numeric(rows["return_pct"], errors="coerce")
    valid_return = rows["return_pct"].map(
        lambda value: pd.notna(value) and math.isfinite(float(value))
    )
    directional = rows["signal"].isin(["LONG", "SHORT"])
    completed = rows["completed"].fillna(False).astype(bool)
    eligible = completed & directional & valid_return

    result = rows.loc[eligible].copy()
    if result.empty:
        return pd.DataFrame(columns=EVALUATION_COLUMNS)

    round_trip_cost_pct = round_trip_bps(cost_model) / 100.0
    result["gross_return_pct"] = result["return_pct"].astype(float)
    result["estimated_cost_pct"] = round_trip_cost_pct
    result["net_return_pct"] = result["gross_return_pct"] - round_trip_cost_pct

    if "benchmark_return_pct" in result.columns:
        benchmark = pd.to_numeric(result["benchmark_return_pct"], errors="coerce")
        benchmark = benchmark.where(
            benchmark.map(lambda value: pd.isna(value) or math.isfinite(float(value)))
        )
        direction = result["signal"].map({"LONG": 1.0, "SHORT": -1.0})
        result["benchmark_return_pct"] = benchmark
        result["directional_benchmark_return_pct"] = benchmark * direction
        result["excess_return_pct"] = (
            result["net_return_pct"] - result["directional_benchmark_return_pct"]
        )
    else:
        result["benchmark_return_pct"] = float("nan")
        result["directional_benchmark_return_pct"] = float("nan")
        result["excess_return_pct"] = float("nan")

    result["evaluated"] = True
    for column in EVALUATION_COLUMNS:
        if column not in result:
            result[column] = pd.NA
    return result[EVALUATION_COLUMNS].reset_index(drop=True)


def summarize_signal_trade_evaluation(evaluation: pd.DataFrame) -> pd.DataFrame:
    """Summarize gross/net returns, cost drag and optional benchmark excess."""
    columns = [
        *GROUP_COLUMNS,
        "trades",
        "avg_gross_return_pct",
        "avg_cost_pct",
        "avg_net_return_pct",
        "net_win_rate_pct",
        "avg_benchmark_return_pct",
        "avg_directional_benchmark_return_pct",
        "avg_excess_return_pct",
        "excess_win_rate_pct",
    ]
    if evaluation.empty:
        return pd.DataFrame(columns=columns)

    required = {*GROUP_COLUMNS, "net_return_pct", "gross_return_pct", "estimated_cost_pct"}
    missing = required.difference(evaluation.columns)
    if missing:
        raise ValueError(
            f"Trade evaluation is missing required columns: {', '.join(sorted(missing))}"
        )

    rows: list[dict[str, object]] = []
    for keys, group in evaluation.groupby(GROUP_COLUMNS, dropna=False, sort=True):
        net = pd.to_numeric(group["net_return_pct"], errors="coerce").dropna()
        gross = pd.to_numeric(group["gross_return_pct"], errors="coerce").dropna()
        costs = pd.to_numeric(group["estimated_cost_pct"], errors="coerce").dropna()
        benchmark = (
            pd.to_numeric(group["directional_benchmark_return_pct"], errors="coerce").dropna()
            if "directional_benchmark_return_pct" in group
            else pd.Series(dtype=float)
        )
        excess = (
            pd.to_numeric(group["excess_return_pct"], errors="coerce").dropna()
            if "excess_return_pct" in group
            else pd.Series(dtype=float)
        )
        rows.append(
            {
                **dict(zip(GROUP_COLUMNS, keys, strict=True)),
                "trades": len(net),
                "avg_gross_return_pct": float(gross.mean()) if not gross.empty else float("nan"),
                "avg_cost_pct": float(costs.mean()) if not costs.empty else float("nan"),
                "avg_net_return_pct": float(net.mean()) if not net.empty else float("nan"),
                "net_win_rate_pct": (
                    float((net > 0.0).mean() * 100.0) if not net.empty else float("nan")
                ),
                "avg_benchmark_return_pct": (
                    float(pd.to_numeric(group["benchmark_return_pct"], errors="coerce").mean())
                    if "benchmark_return_pct" in group
                    else float("nan")
                ),
                "avg_directional_benchmark_return_pct": (
                    float(benchmark.mean()) if not benchmark.empty else float("nan")
                ),
                "avg_excess_return_pct": (
                    float(excess.mean()) if not excess.empty else float("nan")
                ),
                "excess_win_rate_pct": (
                    float((excess > 0.0).mean() * 100.0) if not excess.empty else float("nan")
                ),
            }
        )
    return pd.DataFrame(rows, columns=columns)
