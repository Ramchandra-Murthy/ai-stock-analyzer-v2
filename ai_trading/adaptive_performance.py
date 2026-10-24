"""Performance analytics for the adaptive AI signal layer."""

# ruff: noqa: I001

from __future__ import annotations

import pandas as pd

from ai_trading.outcome_learning import confidence_bucket

PERFORMANCE_COLUMNS = [
    "group",
    "signals",
    "wins",
    "win_rate_pct",
    "avg_return_pct",
    "avg_confidence_pct",
    "confidence_gap_pct",
    "avg_adaptive_adjustment_pct",
]


def adaptive_performance_summary(
    history: pd.DataFrame,
    *,
    group_by: str = "signal",
) -> pd.DataFrame:
    """Compare realized outcomes with the confidence used by adaptive signals."""
    if history.empty:
        return pd.DataFrame(columns=PERFORMANCE_COLUMNS)
    if "adaptive_confidence_pct" not in history.columns:
        return pd.DataFrame(columns=PERFORMANCE_COLUMNS)

    required = {"completed", "return_pct", "confidence_pct", group_by}
    if not required.issubset(history.columns):
        return pd.DataFrame(columns=PERFORMANCE_COLUMNS)

    completed = history[history["completed"]].copy()
    completed["return_pct"] = pd.to_numeric(completed["return_pct"], errors="coerce")
    completed["confidence_pct"] = pd.to_numeric(completed["confidence_pct"], errors="coerce")
    completed["adaptive_confidence_pct"] = pd.to_numeric(
        completed["adaptive_confidence_pct"], errors="coerce"
    )
    completed = completed.dropna(subset=["return_pct", "confidence_pct", "adaptive_confidence_pct"])
    if completed.empty:
        return pd.DataFrame(columns=PERFORMANCE_COLUMNS)

    completed["win"] = completed["return_pct"] > 0.0
    completed["adaptive_adjustment_pct"] = (
        completed["adaptive_confidence_pct"] - completed["confidence_pct"]
    )
    summary = (
        completed.groupby(group_by, as_index=False)
        .agg(
            signals=("return_pct", "size"),
            wins=("win", "sum"),
            win_rate_pct=("win", lambda values: values.mean() * 100.0),
            avg_return_pct=("return_pct", "mean"),
            avg_confidence_pct=("adaptive_confidence_pct", "mean"),
            avg_adaptive_adjustment_pct=("adaptive_adjustment_pct", "mean"),
        )
        .rename(columns={group_by: "group"})
    )
    summary["confidence_gap_pct"] = summary["avg_confidence_pct"] - summary["win_rate_pct"]
    numeric = [
        "win_rate_pct",
        "avg_return_pct",
        "avg_confidence_pct",
        "confidence_gap_pct",
        "avg_adaptive_adjustment_pct",
    ]
    summary[numeric] = summary[numeric].round(2)
    return summary[PERFORMANCE_COLUMNS].sort_values("group").reset_index(drop=True)


def adaptive_confidence_bucket_summary(history: pd.DataFrame) -> pd.DataFrame:
    """Measure realized outcomes across adaptive confidence buckets."""
    if history.empty or "adaptive_confidence_pct" not in history.columns:
        return pd.DataFrame(columns=PERFORMANCE_COLUMNS)

    bucketed = history.copy()
    confidence = pd.to_numeric(
        bucketed["adaptive_confidence_pct"],
        errors="coerce",
    )
    bucketed["adaptive_confidence_bucket"] = confidence.map(
        lambda value: confidence_bucket(value) if pd.notna(value) else None
    )
    return adaptive_performance_summary(
        bucketed,
        group_by="adaptive_confidence_bucket",
    )


def adaptive_effect_summary(history: pd.DataFrame) -> dict[str, float]:
    """Return aggregate raw-vs-adaptive confidence and outcome metrics."""
    if history.empty or "adaptive_confidence_pct" not in history.columns:
        return {
            "completed": 0.0,
            "average_raw_confidence_pct": 0.0,
            "average_adaptive_confidence_pct": 0.0,
            "average_adjustment_pct": 0.0,
            "win_rate_pct": 0.0,
            "average_return_pct": 0.0,
        }

    completed = history[history["completed"]].copy()
    if completed.empty:
        return {
            "completed": 0.0,
            "average_raw_confidence_pct": 0.0,
            "average_adaptive_confidence_pct": 0.0,
            "average_adjustment_pct": 0.0,
            "win_rate_pct": 0.0,
            "average_return_pct": 0.0,
        }

    raw = pd.to_numeric(completed["confidence_pct"], errors="coerce")
    adaptive = pd.to_numeric(completed["adaptive_confidence_pct"], errors="coerce")
    returns = pd.to_numeric(completed["return_pct"], errors="coerce")
    valid = pd.DataFrame({"raw": raw, "adaptive": adaptive, "return": returns}).dropna()
    if valid.empty:
        return {
            "completed": 0.0,
            "average_raw_confidence_pct": 0.0,
            "average_adaptive_confidence_pct": 0.0,
            "average_adjustment_pct": 0.0,
            "win_rate_pct": 0.0,
            "average_return_pct": 0.0,
        }

    return {
        "completed": float(len(valid)),
        "average_raw_confidence_pct": round(float(valid["raw"].mean()), 2),
        "average_adaptive_confidence_pct": round(float(valid["adaptive"].mean()), 2),
        "average_adjustment_pct": round(float((valid["adaptive"] - valid["raw"]).mean()), 2),
        "win_rate_pct": round(float((valid["return"] > 0.0).mean() * 100.0), 2),
        "average_return_pct": round(float(valid["return"].mean()), 2),
    }
