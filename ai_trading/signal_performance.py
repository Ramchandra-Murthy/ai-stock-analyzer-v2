"""Performance and reliability metrics for completed AI signal outcomes.

Metrics are descriptive, not a live portfolio backtest. Each signal is treated
as one equally weighted observation; overlapping positions, execution costs,
capital constraints and slippage are not modeled.
"""

from __future__ import annotations

import math

import pandas as pd

GROUP_COLUMNS = ["signal", "horizon_days", "exchange"]
PERFORMANCE_COLUMNS = [
    *GROUP_COLUMNS,
    "completed",
    "wins",
    "losses",
    "breakeven",
    "win_rate_pct",
    "win_rate_ci_low_pct",
    "win_rate_ci_high_pct",
    "avg_return_pct",
    "median_return_pct",
    "avg_win_pct",
    "avg_loss_pct",
    "expectancy_pct",
    "profit_factor",
    "max_drawdown_pct",
    "longest_losing_streak",
]


def _wilson_interval(wins: int, samples: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Return a two-sided 95% Wilson score interval in percentage points."""
    if samples <= 0:
        return (float("nan"), float("nan"))
    proportion = wins / samples
    denominator = 1.0 + z * z / samples
    center = (proportion + z * z / (2.0 * samples)) / denominator
    margin = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / samples
            + z * z / (4.0 * samples * samples)
        )
        / denominator
    )
    return (max(0.0, center - margin) * 100.0, min(1.0, center + margin) * 100.0)


def _max_drawdown_pct(returns: pd.Series) -> float:
    """Calculate peak-to-trough drawdown for an equal-weight sequential proxy."""
    ordered = returns.copy()
    equity = (1.0 + ordered.clip(lower=-100.0) / 100.0).cumprod()
    peaks = equity.cummax().clip(lower=1.0)
    drawdowns = (equity / peaks - 1.0) * 100.0
    return float(drawdowns.min()) if not drawdowns.empty else float("nan")


def _longest_losing_streak(returns: pd.Series) -> int:
    longest = current = 0
    for value in returns:
        if value < 0.0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def summarize_signal_performance(history: pd.DataFrame) -> pd.DataFrame:
    """Summarize completed outcomes by signal, horizon and exchange.

    Break-even observations count in the sample size and expectancy, but are
    neither wins nor losses. Confidence bounds use the Wilson interval for the
    observed win proportion. Profit factor is undefined when there are no
    losing observations (rather than reporting a misleading finite value).
    """
    if history.empty:
        return pd.DataFrame(columns=PERFORMANCE_COLUMNS)
    required = {"completed", "return_pct", *GROUP_COLUMNS}
    missing = required.difference(history.columns)
    if missing:
        raise ValueError(f"Signal history is missing required columns: {', '.join(sorted(missing))}")

    completed = history.loc[history["completed"].fillna(False)].copy()
    completed["return_pct"] = pd.to_numeric(completed["return_pct"], errors="coerce")
    completed = completed.loc[
        completed["return_pct"].map(lambda value: pd.notna(value) and math.isfinite(float(value)))
    ]
    if completed.empty:
        return pd.DataFrame(columns=PERFORMANCE_COLUMNS)

    if "timestamp" in completed.columns:
        completed = completed.sort_values("timestamp", kind="stable")

    rows: list[dict[str, object]] = []
    for keys, group in completed.groupby(GROUP_COLUMNS, dropna=False, sort=True):
        returns = group["return_pct"].astype(float).reset_index(drop=True)
        wins = int((returns > 0.0).sum())
        losses = int((returns < 0.0).sum())
        breakeven = int((returns == 0.0).sum())
        gross_profit = float(returns.loc[returns > 0.0].sum())
        gross_loss = float(-returns.loc[returns < 0.0].sum())
        ci_low, ci_high = _wilson_interval(wins, len(returns))
        rows.append(
            {
                **dict(zip(GROUP_COLUMNS, keys, strict=True)),
                "completed": len(returns),
                "wins": wins,
                "losses": losses,
                "breakeven": breakeven,
                "win_rate_pct": wins / len(returns) * 100.0,
                "win_rate_ci_low_pct": ci_low,
                "win_rate_ci_high_pct": ci_high,
                "avg_return_pct": float(returns.mean()),
                "median_return_pct": float(returns.median()),
                "avg_win_pct": float(returns.loc[returns > 0.0].mean())
                if wins
                else float("nan"),
                "avg_loss_pct": float(returns.loc[returns < 0.0].mean())
                if losses
                else float("nan"),
                "expectancy_pct": float(returns.mean()),
                "profit_factor": gross_profit / gross_loss if gross_loss > 0.0 else float("nan"),
                "max_drawdown_pct": _max_drawdown_pct(returns),
                "longest_losing_streak": _longest_losing_streak(returns),
            }
        )
    return pd.DataFrame(rows, columns=PERFORMANCE_COLUMNS)
