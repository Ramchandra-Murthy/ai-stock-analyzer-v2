"""Chronological walk-forward validation for momentum-score observations.

Research-only: this module summarizes already-computed forward returns and does
not fetch data, create trading signals, or change scanner rankings.
"""

from __future__ import annotations

import math
import random
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
    spread_ci_lower_pct: float | None
    spread_ci_upper_pct: float | None
    low_sample_fold_count: int
    insufficient_evidence: bool
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
    min_observations_per_fold: int = 20,
    n_bootstrap: int = 2000,
    confidence_level: float = 0.95,
    random_seed: int = 42,
) -> MomentumWalkForwardReport:
    """Evaluate score/return relationships across chronological equal-sized folds.

    Dates must be sortable ISO-8601 date strings (YYYY-MM-DD). Observations are
    sorted chronologically before splitting; each fold is evaluated independently.
    The caller is responsible for point-in-time-safe scores and non-overlapping
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
    if isinstance(n_bootstrap, bool) or not isinstance(n_bootstrap, int) or n_bootstrap < 100:
        raise ValueError("n_bootstrap must be an integer of at least 100")
    if (
        isinstance(confidence_level, bool)
        or not isinstance(confidence_level, (int, float))
        or not math.isfinite(confidence_level)
        or not 0 < confidence_level < 1
    ):
        raise ValueError("confidence_level must be between 0 and 1")
    if isinstance(random_seed, bool) or not isinstance(random_seed, int):
        raise ValueError("random_seed must be an integer")

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
    ci_lower = ci_upper = None
    if eligible_spread_count >= 2:
        rng = random.Random(random_seed)
        sample_size = eligible_spread_count
        bootstrap_means = [
            sum(rng.choices(eligible_spreads, k=sample_size)) / sample_size
            for _ in range(n_bootstrap)
        ]
        ordered = sorted(bootstrap_means)

        def percentile(p: float) -> float:
            position = (len(ordered) - 1) * p
            lower_index = math.floor(position)
            upper_index = math.ceil(position)
            if lower_index == upper_index:
                return ordered[lower_index]
            fraction = position - lower_index
            return ordered[lower_index] + fraction * (ordered[upper_index] - ordered[lower_index])

        tail = (1.0 - float(confidence_level)) / 2.0
        ci_lower = percentile(tail)
        ci_upper = percentile(1.0 - tail)
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
        spread_ci_lower_pct=ci_lower,
        spread_ci_upper_pct=ci_upper,
        low_sample_fold_count=low_sample_fold_count,
        insufficient_evidence=low_sample_fold_count > 0 or eligible_spread_count < 2,
        folds=tuple(folds),
    )
