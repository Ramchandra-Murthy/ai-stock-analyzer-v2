"""Regime-aware signal composition for NSE/BSE research."""

from __future__ import annotations

from dataclasses import dataclass

from algorithmic_trading.edge_engine import EdgeMetrics


@dataclass(frozen=True)
class SignalDecision:
    """Transparent signal state built from observable components."""

    direction: str
    score: float
    regime: str
    relative_return_pct: float | None
    expectancy: float | None
    edge_qualified: bool
    reasons: tuple[str, ...]


def compose_signal(
    regime: str,
    regime_score: int,
    relative_return_pct: float | None = None,
    edge: EdgeMetrics | None = None,
    min_expectancy: float = 0.0,
) -> SignalDecision:
    """Combine regime, relative strength and measured edge transparently.

    This is a research signal, not a prediction or an order instruction.
    The score is deliberately bounded to make the contributing components
    easy to inspect in the algorithmic dashboard.
    """
    score = max(-100.0, min(100.0, float(regime_score) * 15.0))
    reasons: list[str] = []

    if regime == "BULLISH":
        reasons.append("bullish regime")
    elif regime == "BEARISH":
        reasons.append("bearish regime")
    else:
        reasons.append("inconclusive regime")

    if relative_return_pct is not None:
        relative_component = max(-30.0, min(30.0, relative_return_pct))
        score += relative_component
        reasons.append(
            "relative strength positive"
            if relative_return_pct > 0
            else "relative strength negative"
        )

    expectancy = None if edge is None else edge.expectancy
    edge_qualified = edge is not None and expectancy >= min_expectancy
    if edge is not None:
        if edge_qualified:
            score += 20.0
            reasons.append("measured edge meets threshold")
        else:
            score -= 20.0
            reasons.append("measured edge below threshold")

    score = max(-100.0, min(100.0, score))
    if regime == "BULLISH" and score >= 30.0:
        direction = "LONG"
    elif regime == "BEARISH" and score <= -30.0:
        direction = "SHORT"
    else:
        direction = "FLAT"

    return SignalDecision(
        direction=direction,
        score=score,
        regime=regime,
        relative_return_pct=relative_return_pct,
        expectancy=expectancy,
        edge_qualified=edge_qualified,
        reasons=tuple(reasons),
    )
