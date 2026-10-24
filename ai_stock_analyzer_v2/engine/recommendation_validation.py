"""Consistency and risk checks for research trade plans.

This module validates recommendation inputs; it does not generate trading signals
or place orders. Scores and labels are treated as supplied diagnostics.
"""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite


def validate_trade_plan(
    *,
    current_price: float,
    target_price: float,
    stop_loss: float,
    direction: str = "LONG",
    min_reward_risk: float = 1.0,
) -> dict[str, object]:
    """Validate target/stop orientation and compute reward-to-risk metrics."""
    values = (current_price, target_price, stop_loss, min_reward_risk)
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
        raise ValueError("prices and min_reward_risk must be numeric")
    if any(not isfinite(float(value)) for value in values):
        raise ValueError("prices and min_reward_risk must be finite")
    if current_price <= 0 or target_price <= 0 or stop_loss <= 0:
        raise ValueError("prices must be positive")
    if min_reward_risk <= 0:
        raise ValueError("min_reward_risk must be positive")

    normalized_direction = direction.strip().upper()
    if normalized_direction not in {"LONG", "SHORT"}:
        raise ValueError("direction must be LONG or SHORT")

    if normalized_direction == "LONG":
        reward = target_price - current_price
        risk = current_price - stop_loss
    else:
        reward = current_price - target_price
        risk = stop_loss - current_price

    issues: list[str] = []
    if reward <= 0:
        issues.append("target is not favorable for the trade direction")
    if risk <= 0:
        issues.append("stop-loss is not protective for the trade direction")

    ratio = reward / risk if reward > 0 and risk > 0 else None
    if ratio is not None and ratio < min_reward_risk:
        issues.append("reward/risk ratio is below the configured minimum")

    return {
        "direction": normalized_direction,
        "reward_per_unit": float(reward),
        "risk_per_unit": float(risk),
        "reward_risk_ratio": float(ratio) if ratio is not None else None,
        "minimum_reward_risk": float(min_reward_risk),
        "valid": not issues,
        "issues": issues,
    }


def reconcile_recommendations(
    *,
    overall: str,
    technical: str | None = None,
    fundamental: str | None = None,
    ai_verdict: str | None = None,
    confidence: float | None = None,
    minimum_confidence: float = 0.0,
    risk_level: str | None = None,
    trade_plan: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Surface recommendation disagreement and missing/unsafe trade-plan inputs."""
    labels = {
        "overall": overall,
        "technical": technical,
        "fundamental": fundamental,
        "ai_verdict": ai_verdict,
    }
    normalized = {
        key: value.strip().upper() if isinstance(value, str) and value.strip() else None
        for key, value in labels.items()
    }
    if normalized["overall"] is None:
        raise ValueError("overall recommendation is required")
    if not 0 <= minimum_confidence <= 100 or not isfinite(minimum_confidence):
        raise ValueError("minimum_confidence must be finite and between 0 and 100")
    if confidence is not None and (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not isfinite(float(confidence))
        or not 0 <= confidence <= 100
    ):
        raise ValueError("confidence must be finite and between 0 and 100")

    actionable = {"BUY", "STRONG BUY", "SELL", "STRONG SELL"}
    directional = {value for value in normalized.values() if value in actionable}
    issues: list[str] = []
    if len(directional.intersection({"BUY", "STRONG BUY"})) and len(
        directional.intersection({"SELL", "STRONG SELL"})
    ):
        issues.append("buy and sell recommendations conflict")
    if normalized["ai_verdict"] in {"INSUFFICIENT DATA", "UNKNOWN", "UNAVAILABLE"}:
        issues.append("AI verdict is unavailable or insufficient")
    if confidence is None:
        issues.append("confidence is missing")
    elif confidence < minimum_confidence:
        issues.append("confidence is below the configured minimum")
    if (
        not isinstance(risk_level, str)
        or not risk_level.strip()
        or risk_level.strip().upper()
        in {
            "UNKNOWN",
            "N/A",
            "NONE",
        }
    ):
        issues.append("risk level is missing or unknown")
    if trade_plan is not None and trade_plan.get("valid") is False:
        issues.append("trade plan failed risk validation")

    return {
        "overall": normalized["overall"],
        "recommendations": normalized,
        "conflict": any("conflict" in issue for issue in issues),
        "review_required": bool(issues),
        "issues": issues,
    }
