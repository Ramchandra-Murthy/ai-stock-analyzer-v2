"""Coverage and status diagnostics for historical benchmark matches."""

from __future__ import annotations

import pandas as pd

MATCHED_STATUS = "matched_daily_close_proxy"


def _coverage_row(
    history: pd.DataFrame,
    *,
    benchmark: str,
    eligible: pd.Series,
    status_column: str,
) -> dict[str, object]:
    eligible_history = history.loc[eligible]
    statuses = (
        eligible_history[status_column].astype("string").fillna("status_missing")
        if status_column in eligible_history
        else pd.Series("status_missing", index=eligible_history.index, dtype="string")
    )
    total = int(len(eligible_history))
    matched = int(statuses.eq(MATCHED_STATUS).sum())
    breakdown = statuses.value_counts().sort_index()
    return {
        "benchmark": benchmark,
        "eligible_observations": total,
        "matched_observations": matched,
        "unmatched_observations": total - matched,
        "coverage_pct": float(matched / total * 100.0) if total else float("nan"),
        "status_breakdown": "; ".join(
            f"{status}: {int(count)}" for status, count in breakdown.items()
        ),
    }


def summarize_benchmark_coverage(history: pd.DataFrame) -> pd.DataFrame:
    """Summarize match coverage without treating unmapped sectors as failed matches.

    NIFTY coverage uses every signal observation. Sector coverage uses only rows
    with a mapped sector benchmark name; unmapped symbols are excluded from its
    denominator and remain visible through the mapped-observation count.
    """
    columns = [
        "benchmark",
        "eligible_observations",
        "matched_observations",
        "unmatched_observations",
        "coverage_pct",
        "status_breakdown",
    ]
    if history.empty:
        return pd.DataFrame(columns=columns)

    nifty_eligible = pd.Series(True, index=history.index)
    if "sector_benchmark_name" in history:
        sector_eligible = history["sector_benchmark_name"].notna()
    else:
        sector_eligible = pd.Series(False, index=history.index)

    rows = [
        _coverage_row(
            history,
            benchmark="NIFTY 50",
            eligible=nifty_eligible,
            status_column="benchmark_status",
        ),
        _coverage_row(
            history,
            benchmark="Mapped sector index",
            eligible=sector_eligible,
            status_column="sector_benchmark_status",
        ),
    ]
    return pd.DataFrame(rows, columns=columns)
