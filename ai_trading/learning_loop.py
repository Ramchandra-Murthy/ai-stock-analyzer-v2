"""Chronological adaptive-learning loop for AI signal confidence."""

from __future__ import annotations

import pandas as pd

from ai_trading.adaptive_engine import (
    apply_adaptive_confidence,
    build_adaptive_adjustments,
)
from ai_trading.outcome_learning import confidence_bucket


def run_learning_loop(
    history: pd.DataFrame,
    *,
    min_samples: int = 10,
    max_adjustment_pct: float = 10.0,
) -> pd.DataFrame:
    """Replay signals chronologically using only outcomes known before each signal.

    The returned frame contains the confidence that would have been available
    at each signal timestamp, preventing later outcomes from leaking backward.
    """
    columns = [
        "timestamp",
        "symbol",
        "signal",
        "regime",
        "raw_confidence_pct",
        "adaptive_confidence_pct",
        "adaptive_adjustment_pct",
        "learning_samples",
        "completed",
        "return_pct",
    ]
    if history.empty:
        return pd.DataFrame(columns=columns)

    required = {"timestamp", "symbol", "signal", "confidence_pct", "completed"}
    if not required.issubset(history.columns):
        return pd.DataFrame(columns=columns)

    working = history.copy()
    working["timestamp"] = pd.to_datetime(working["timestamp"], errors="coerce")
    working = working.dropna(subset=["timestamp"]).sort_values("timestamp")
    if working.empty:
        return pd.DataFrame(columns=columns)

    if "regime" not in working.columns:
        working["regime"] = "ALL"
    if "return_pct" not in working.columns:
        working["return_pct"] = None

    rows: list[dict[str, object]] = []
    prior_completed = working.iloc[0:0].copy()

    for _, timestamp_rows in working.groupby("timestamp", sort=True):
        # Every signal at one timestamp sees only outcomes from strictly earlier
        # timestamps. Outcomes completed at this timestamp are added after the group.
        adjustments = build_adaptive_adjustments(
            prior_completed,
            min_samples=min_samples,
            max_adjustment_pct=max_adjustment_pct,
        )
        for _, row in timestamp_rows.iterrows():
            raw_confidence = float(row["confidence_pct"])
            signal = str(row["signal"])
            regime = str(row["regime"])
            adaptive_confidence = apply_adaptive_confidence(
                raw_confidence,
                signal=signal,
                regime=regime,
                adjustments=adjustments,
            )
            exact = adjustments[
                (adjustments["signal"] == signal)
                & (adjustments["regime"] == regime)
                & (adjustments["confidence_bucket"] == confidence_bucket(raw_confidence))
            ]
            fallback = adjustments[
                (adjustments["signal"] == signal)
                & (adjustments["regime"] == "ALL")
                & (adjustments["confidence_bucket"] == confidence_bucket(raw_confidence))
            ]
            matches = exact if not exact.empty else fallback
            samples = int(matches.iloc[0]["samples"]) if not matches.empty else 0
            rows.append(
                {
                    "timestamp": row["timestamp"],
                    "symbol": str(row["symbol"]),
                    "signal": signal,
                    "regime": regime,
                    "raw_confidence_pct": raw_confidence,
                    "adaptive_confidence_pct": adaptive_confidence,
                    "adaptive_adjustment_pct": round(adaptive_confidence - raw_confidence, 1),
                    "learning_samples": samples,
                    "completed": bool(row["completed"]),
                    "return_pct": row["return_pct"],
                }
            )

        completed_rows = timestamp_rows.loc[timestamp_rows["completed"].astype(bool)]
        if not completed_rows.empty:
            prior_completed = pd.concat(
                [prior_completed, completed_rows],
                ignore_index=True,
            )

    return pd.DataFrame(rows, columns=columns)


def learning_loop_summary(replay: pd.DataFrame) -> dict[str, float]:
    """Return compact learning-loop status metrics."""
    if replay.empty:
        return {
            "signals": 0.0,
            "completed": 0.0,
            "learned_signals": 0.0,
            "average_adjustment_pct": 0.0,
            "maximum_adjustment_pct": 0.0,
        }

    adjustment = pd.to_numeric(replay["adaptive_adjustment_pct"], errors="coerce").fillna(0.0)
    learned = adjustment.abs() > 1e-9
    return {
        "signals": float(len(replay)),
        "completed": float(replay["completed"].sum()),
        "learned_signals": float(learned.sum()),
        "average_adjustment_pct": round(float(adjustment.mean()), 2),
        "maximum_adjustment_pct": round(float(adjustment.abs().max()), 2),
    }
