"""Outcome-learning analytics for historical AI trading signals."""

import pandas as pd  # noqa: I001

LEARNING_COLUMNS = [
    "group",
    "signals",
    "wins",
    "win_rate_pct",
    "avg_return_pct",
    "median_return_pct",
    "avg_confidence_pct",
    "confidence_gap_pct",
]


def confidence_bucket(confidence_pct: float) -> str:
    """Map a confidence percentage into a stable monitoring bucket."""
    if confidence_pct < 55.0:
        return "<55%"
    if confidence_pct < 65.0:
        return "55-65%"
    if confidence_pct < 75.0:
        return "65-75%"
    return "75%+"


def outcome_learning_summary(
    history: pd.DataFrame,
    *,
    group_by: str = "signal",
) -> pd.DataFrame:
    """Summarize completed signal outcomes for monitoring and calibration."""
    required = {"completed", "return_pct", "confidence_pct", group_by}
    if history.empty or not required.issubset(history.columns):
        return pd.DataFrame(columns=LEARNING_COLUMNS)

    completed = history[history["completed"]].copy()
    completed["return_pct"] = pd.to_numeric(completed["return_pct"], errors="coerce")
    completed["confidence_pct"] = pd.to_numeric(completed["confidence_pct"], errors="coerce")
    completed = completed.dropna(subset=["return_pct", "confidence_pct"])
    if completed.empty:
        return pd.DataFrame(columns=LEARNING_COLUMNS)

    completed["win"] = completed["return_pct"] > 0.0
    summary = (
        completed.groupby(group_by, as_index=False)
        .agg(
            signals=("return_pct", "size"),
            wins=("win", "sum"),
            win_rate_pct=("win", lambda values: values.mean() * 100.0),
            avg_return_pct=("return_pct", "mean"),
            median_return_pct=("return_pct", "median"),
            avg_confidence_pct=("confidence_pct", "mean"),
        )
        .rename(columns={group_by: "group"})
    )
    summary["confidence_gap_pct"] = summary["avg_confidence_pct"] - summary["win_rate_pct"]
    numeric = [
        "win_rate_pct",
        "avg_return_pct",
        "median_return_pct",
        "avg_confidence_pct",
        "confidence_gap_pct",
    ]
    summary[numeric] = summary[numeric].round(2)
    return summary[LEARNING_COLUMNS].sort_values("group").reset_index(drop=True)


def confidence_learning_summary(history: pd.DataFrame) -> pd.DataFrame:
    """Measure realized outcomes across AI confidence buckets."""
    if history.empty or "confidence_pct" not in history.columns:
        return pd.DataFrame(columns=LEARNING_COLUMNS)

    bucketed = history.copy()
    confidence = pd.to_numeric(bucketed["confidence_pct"], errors="coerce")
    bucketed["confidence_bucket"] = confidence.map(
        lambda value: confidence_bucket(value) if pd.notna(value) else None
    )
    return outcome_learning_summary(bucketed, group_by="confidence_bucket")


def regime_learning_summary(history: pd.DataFrame) -> pd.DataFrame:
    """Measure realized outcomes by recorded market regime when available."""
    if "regime" not in history.columns:
        return pd.DataFrame(columns=LEARNING_COLUMNS)
    return outcome_learning_summary(history, group_by="regime")
