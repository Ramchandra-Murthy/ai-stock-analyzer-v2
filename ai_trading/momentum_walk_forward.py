"""Chronological walk-forward validation for momentum-score observations.

Research-only: this module summarizes already-computed forward returns and does
not fetch data, create trading signals, or change scanner rankings.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any

from ai_trading.momentum_validation import evaluate_momentum_scores


@dataclass(frozen=True)
class MomentumWalkForwardFold:
    """Metrics for one contiguous chronological evaluation fold."""

    fold: int
    start_date: str
    end_date: str
    observation_count: int
    mean_forward_return_pct: float | None
    win_rate_pct: float | None
    score_return_correlation: float | None
    top_minus_bottom_return_pct: float | None


@dataclass(frozen=True)
class MomentumWalkForwardReport:
    """Fold-level results and a compact stability summary."""

    observation_count: int
    fold_count: int
    positive_spread_fold_count: int
    positive_spread_fold_rate_pct: float | None
    folds: tuple[MomentumWalkForwardFold, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""
        return asdict(self)


def evaluate_momentum_walk_forward(
    observations: Iterable[Mapping[str, Any]],
    *,
    date_key: str = "date",
    score_key: str = "momentum_score",
    return_key: str = "forward_return_pct",
    n_splits: int = 5,
) -> MomentumWalkForwardReport:
    """Evaluate score/return relationships across chronological equal-sized folds.

    Dates must be sortable ISO-8601 date strings (YYYY-MM-DD). Observations are
    sorted chronologically before splitting; each fold is evaluated independently.
    The caller is responsible for point-in-time-safe scores and non-overlapping
    forward-return labels.
    """
    if isinstance(n_splits, bool) or not isinstance(n_splits, int) or n_splits < 2:
        raise ValueError("n_splits must be an integer of at least 2")

    rows = list(observations)
    normalized: list[tuple[str, Mapping[str, Any]]] = []
    for row in rows:
        try:
            date_value = row[date_key]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"each observation must contain {date_key}") from exc
        if not isinstance(date_value, str) or len(date_value) != 10:
            raise ValueError(f"{date_key} must be an ISO-8601 date string (YYYY-MM-DD)")
        try:
            from datetime import date

            date.fromisoformat(date_value)
        except ValueError as exc:
            raise ValueError(f"{date_key} must be a valid ISO-8601 date") from exc
        normalized.append((date_value, row))

    normalized.sort(key=lambda item: item[0])
    if len(normalized) < n_splits:
        raise ValueError("observations must be at least n_splits")

    quotient, remainder = divmod(len(normalized), n_splits)
    folds: list[MomentumWalkForwardFold] = []
    offset = 0
    for index in range(n_splits):
        fold_size = quotient + (1 if index < remainder else 0)
        fold_rows = normalized[offset : offset + fold_size]
        offset += fold_size
        metrics = evaluate_momentum_scores(
            [row for _, row in fold_rows],
            score_key=score_key,
            return_key=return_key,
        )
        folds.append(
            MomentumWalkForwardFold(
                fold=index + 1,
                start_date=fold_rows[0][0],
                end_date=fold_rows[-1][0],
                observation_count=metrics.observation_count,
                mean_forward_return_pct=metrics.mean_forward_return_pct,
                win_rate_pct=metrics.win_rate_pct,
                score_return_correlation=metrics.score_return_correlation,
                top_minus_bottom_return_pct=metrics.top_minus_bottom_return_pct,
            )
        )

    positive_spread_count = sum(
        fold.top_minus_bottom_return_pct is not None
        and fold.top_minus_bottom_return_pct > 0
        for fold in folds
    )
    eligible_spread_count = sum(
        fold.top_minus_bottom_return_pct is not None for fold in folds
    )
    return MomentumWalkForwardReport(
        observation_count=len(normalized),
        fold_count=len(folds),
        positive_spread_fold_count=positive_spread_count,
        positive_spread_fold_rate_pct=(
            100.0 * positive_spread_count / eligible_spread_count
            if eligible_spread_count
            else None
        ),
        folds=tuple(folds),
    )
