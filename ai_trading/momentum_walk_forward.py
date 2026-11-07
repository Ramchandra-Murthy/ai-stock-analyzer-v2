"""Chronological walk-forward validation for momentum-score observations.

Research-only: this module summarizes already-computed forward returns and does
not fetch data, create trading signals, or change scanner rankings.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import date
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
    low_sample_warning: bool


@dataclass(frozen=True)
class MomentumWalkForwardReport:
    """Fold-level results and a compact stability summary."""

    observation_count: int
    fold_count: int
    positive_spread_fold_count: int
    positive_spread_fold_rate_pct: float | None
    mean_spread_pct: float | None
    spread_std_dev_pct: float | None
    low_sample_fold_count: int
    insufficient_evidence: bool
    folds: tuple[MomentumWalkForwardFold, ...]
    purged_observation_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""
        return asdict(self)


def _validate_iso_date(value: Any, *, key: str) -> str:
    """Require the canonical YYYY-MM-DD representation used for sorting."""
    if not isinstance(value, str):
        raise ValueError(f"{key} must be an ISO-8601 date string (YYYY-MM-DD)")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be a valid ISO-8601 date") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{key} must use the canonical YYYY-MM-DD format")
    return value


def evaluate_momentum_walk_forward(
    observations: Iterable[Mapping[str, Any]],
    *,
    date_key: str = "date",
    score_key: str = "momentum_score",
    return_key: str = "forward_return_pct",
    label_end_key: str | None = None,
    n_splits: int = 5,
    min_observations_per_fold: int = 20,
) -> MomentumWalkForwardReport:
    """Evaluate score/return relationships across chronological equal-sized folds.

    Dates must use canonical YYYY-MM-DD strings. Observations are sorted
    chronologically before splitting; each fold is evaluated independently.
    When label_end_key is supplied, observations whose forward-return label
    reaches the next fold's start date are purged from the earlier fold. The
    caller remains responsible for point-in-time-safe scores and complete labels.
    Without label_end_key, the caller is also responsible for non-overlapping
    forward-return labels.
    """
    if (
        isinstance(min_observations_per_fold, bool)
        or not isinstance(min_observations_per_fold, int)
        or min_observations_per_fold < 1
    ):
        raise ValueError("min_observations_per_fold must be a positive integer")

    if isinstance(n_splits, bool) or not isinstance(n_splits, int) or n_splits < 2:
        raise ValueError("n_splits must be an integer of at least 2")

    rows = list(observations)
    normalized: list[tuple[str, str | None, Mapping[str, Any]]] = []
    for row in rows:
        try:
            date_value = row[date_key]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"each observation must contain {date_key}") from exc
        observation_date = _validate_iso_date(date_value, key=date_key)
        label_end = None
        if label_end_key is not None:
            try:
                label_end = _validate_iso_date(row[label_end_key], key=label_end_key)
            except (KeyError, TypeError) as exc:
                raise ValueError(f"each observation must contain {label_end_key}") from exc
            if label_end < observation_date:
                raise ValueError(f"{label_end_key} must not precede {date_key}")
        normalized.append((observation_date, label_end, row))

    normalized.sort(key=lambda item: item[0])
    date_groups: list[list[tuple[str, str | None, Mapping[str, Any]]]] = []
    for item in normalized:
        if not date_groups or date_groups[-1][0][0] != item[0]:
            date_groups.append([])
        date_groups[-1].append(item)
    if len(date_groups) < n_splits:
        raise ValueError("observations must contain at least n_splits distinct dates")

    quotient, remainder = divmod(len(date_groups), n_splits)
    raw_folds: list[list[tuple[str, str | None, Mapping[str, Any]]]] = []
    offset = 0
    for index in range(n_splits):
        fold_size = quotient + (1 if index < remainder else 0)
        fold_groups = date_groups[offset : offset + fold_size]
        raw_folds.append([item for group in fold_groups for item in group])
        offset += fold_size

    folds: list[MomentumWalkForwardFold] = []
    purged_observation_count = 0
    for index, raw_fold in enumerate(raw_folds):
        fold_rows = raw_fold
        if label_end_key is not None and index < len(raw_folds) - 1:
            next_fold_start = raw_folds[index + 1][0][0]
            retained_rows = [
                item for item in raw_fold if item[1] is not None and item[1] < next_fold_start
            ]
            purged_observation_count += len(raw_fold) - len(retained_rows)
            fold_rows = retained_rows
        if not fold_rows:
            raise ValueError(
                f"label purging left fold {index + 1} empty; use fewer splits or more history"
            )

        metrics = evaluate_momentum_scores(
            [row for _, _, row in fold_rows],
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
                low_sample_warning=metrics.observation_count < min_observations_per_fold,
            )
        )

    positive_spread_count = sum(
        fold.top_minus_bottom_return_pct is not None and fold.top_minus_bottom_return_pct > 0
        for fold in folds
    )
    eligible_spreads = [
        fold.top_minus_bottom_return_pct
        for fold in folds
        if fold.top_minus_bottom_return_pct is not None
    ]
    eligible_spread_count = len(eligible_spreads)
    mean_spread = sum(eligible_spreads) / eligible_spread_count if eligible_spread_count else None
    spread_std_dev = (
        math.sqrt(
            sum((spread - mean_spread) ** 2 for spread in eligible_spreads) / eligible_spread_count
        )
        if eligible_spread_count and mean_spread is not None
        else None
    )
    low_sample_fold_count = sum(fold.low_sample_warning for fold in folds)
    return MomentumWalkForwardReport(
        observation_count=len(normalized),
        fold_count=len(folds),
        positive_spread_fold_count=positive_spread_count,
        positive_spread_fold_rate_pct=(
            100.0 * positive_spread_count / eligible_spread_count if eligible_spread_count else None
        ),
        mean_spread_pct=mean_spread,
        spread_std_dev_pct=spread_std_dev,
        low_sample_fold_count=low_sample_fold_count,
        insufficient_evidence=low_sample_fold_count > 0 or eligible_spread_count < 2,
        folds=tuple(folds),
        purged_observation_count=purged_observation_count,
    )
