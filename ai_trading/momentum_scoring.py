"""Deterministic, explainable momentum component scoring."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_WEIGHTS: dict[str, float] = {
    "trend": 0.30,
    "relative_strength": 0.25,
    "volume_expansion": 0.20,
    "breakout_quality": 0.25,
}


@dataclass(frozen=True)
class MomentumScore:
    """Weighted momentum score and its component-level explanation."""

    score: float | None
    components: dict[str, float | None]
    weights: dict[str, float]
    explanation: str


def score_momentum(
    components: Mapping[str, float | None],
    *,
    weights: Mapping[str, float] | None = None,
) -> MomentumScore:
    """Score pre-normalized momentum components on a 0–100 scale.

    Component values must already be normalized to 0–100 by the caller.
    Missing components are omitted and the remaining weights are
    renormalized. Unknown component names and invalid values are rejected.
    """
    selected_weights = dict(DEFAULT_WEIGHTS if weights is None else weights)
    if set(selected_weights) != set(DEFAULT_WEIGHTS):
        raise ValueError(f"weights must define exactly: {sorted(DEFAULT_WEIGHTS)}")

    for name, weight in selected_weights.items():
        if not math.isfinite(weight) or weight < 0:
            raise ValueError(f"weight for {name} must be finite and non-negative")
    if sum(selected_weights.values()) <= 0:
        raise ValueError("at least one weight must be positive")

    unknown = set(components).difference(DEFAULT_WEIGHTS)
    if unknown:
        raise ValueError(f"unknown momentum components: {sorted(unknown)}")

    normalized: dict[str, float | None] = {}
    for name in DEFAULT_WEIGHTS:
        value = components.get(name)
        if value is None:
            normalized[name] = None
            continue
        numeric = float(value)
        if not math.isfinite(numeric) or not 0 <= numeric <= 100:
            raise ValueError(f"component {name} must be finite and within 0–100")
        normalized[name] = numeric

    active = {
        name: weight
        for name, weight in selected_weights.items()
        if normalized[name] is not None and weight > 0
    }
    if not active:
        return MomentumScore(
            score=None,
            components=normalized,
            weights=selected_weights,
            explanation="Momentum score unavailable: no valid weighted components.",
        )

    total_weight = sum(active.values())
    score = sum(float(normalized[name]) * weight for name, weight in active.items())
    score = round(score / total_weight, 2)

    ranked = sorted(
        active,
        key=lambda name: float(normalized[name]),
        reverse=True,
    )
    strongest = ranked[0]
    weakest = ranked[-1]
    explanation = (
        f"Momentum {score:.2f}/100; strongest: {strongest.replace('_', ' ')} "
        f"({normalized[strongest]:.1f}); weakest: {weakest.replace('_', ' ')} "
        f"({normalized[weakest]:.1f})."
    )
    return MomentumScore(
        score=score,
        components=normalized,
        weights=selected_weights,
        explanation=explanation,
    )
