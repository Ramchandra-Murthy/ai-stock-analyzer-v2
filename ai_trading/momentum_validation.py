"""Research-only validation of momentum scores against forward returns.

This module does not create trading signals. It summarizes historical observations
to help assess whether score rankings have predictive value.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any

DEFAULT_SCORE_BINS: tuple[tuple[float, float], ...] = (
    (0.0, 20.0),
    (20.0, 40.0),
    (40.0, 60.0),
    (60.0, 80.0),
    (80.0, 100.0),
)


@dataclass(frozen=True)
class MomentumBucketResult:
    """Summary statistics for one momentum-score interval."""

    lower_score: float
    upper_score: float
    count: int
    mean_forward_return_pct: float | None
    median_forward_return_pct: float | None
    win_rate_pct: float | None


@dataclass(frozen=True)
class MomentumValidationReport:
    """Aggregated score/forward-return validation statistics."""

    observation_count: int
    mean_forward_return_pct: float | None
    median_forward_return_pct: float | None
    win_rate_pct: float | None
    score_return_correlation: float | None
    top_bucket_mean_return_pct: float | None
    bottom_bucket_mean_return_pct: float | None
    top_minus_bottom_return_pct: float | None
    buckets: tuple[MomentumBucketResult, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""
        return asdict(self)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _correlation(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    x_delta = [value - x_mean for value in xs]
    y_delta = [value - y_mean for value in ys]
    x_variance = sum(value * value for value in x_delta)
    y_variance = sum(value * value for value in y_delta)
    denominator = math.sqrt(x_variance * y_variance)
    if denominator == 0:
        return None
    return sum(x * y for x, y in zip(x_delta, y_delta, strict=True)) / denominator


def evaluate_momentum_scores(
    observations: Iterable[Mapping[str, float]],
    *,
    score_key: str = "momentum_score",
    return_key: str = "forward_return_pct",
    score_bins: tuple[tuple[float, float], ...] = DEFAULT_SCORE_BINS,
) -> MomentumValidationReport:
    """Evaluate normalized momentum scores against realized forward returns.

    Each observation must contain a score in [0, 100] and a finite forward
    return expressed in percentage points. Intervals are left-closed/right-open,
    except the final interval which includes its upper bound.
    """
    if not score_bins:
        raise ValueError("score_bins must not be empty")
    previous_upper = 0.0
    for index, (lower, upper) in enumerate(score_bins):
        if (
            not math.isfinite(lower)
            or not math.isfinite(upper)
            or lower < 0
            or upper > 100
            or lower >= upper
            or (index > 0 and lower != previous_upper)
        ):
            raise ValueError("score_bins must be contiguous increasing intervals within 0–100")
        previous_upper = upper
    if score_bins[0][0] != 0 or score_bins[-1][1] != 100:
        raise ValueError("score_bins must cover the full 0–100 score range")

    scores: list[float] = []
    returns: list[float] = []
    for row in observations:
        try:
            score = float(row[score_key])
            forward_return = float(row[return_key])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"each observation must contain numeric {score_key} and {return_key}"
            ) from exc
        if not math.isfinite(score) or not 0 <= score <= 100:
            raise ValueError(f"{score_key} must be finite and within 0–100")
        if not math.isfinite(forward_return):
            raise ValueError(f"{return_key} must be finite")
        scores.append(score)
        returns.append(forward_return)

    bucket_results: list[MomentumBucketResult] = []
    for index, (lower, upper) in enumerate(score_bins):
        bucket_returns = [
            forward_return
            for score, forward_return in zip(scores, returns, strict=True)
            if lower <= score < upper or (index == len(score_bins) - 1 and score == upper)
        ]
        bucket_results.append(
            MomentumBucketResult(
                lower_score=lower,
                upper_score=upper,
                count=len(bucket_returns),
                mean_forward_return_pct=_mean(bucket_returns),
                median_forward_return_pct=_median(bucket_returns),
                win_rate_pct=(
                    100.0 * sum(value > 0 for value in bucket_returns) / len(bucket_returns)
                    if bucket_returns
                    else None
                ),
            )
        )

    bottom_mean = bucket_results[0].mean_forward_return_pct
    top_mean = bucket_results[-1].mean_forward_return_pct
    spread = top_mean - bottom_mean if top_mean is not None and bottom_mean is not None else None
    return MomentumValidationReport(
        observation_count=len(scores),
        mean_forward_return_pct=_mean(returns),
        median_forward_return_pct=_median(returns),
        win_rate_pct=(
            100.0 * sum(value > 0 for value in returns) / len(returns) if returns else None
        ),
        score_return_correlation=_correlation(scores, returns),
        top_bucket_mean_return_pct=top_mean,
        bottom_bucket_mean_return_pct=bottom_mean,
        top_minus_bottom_return_pct=spread,
        buckets=tuple(bucket_results),
    )
