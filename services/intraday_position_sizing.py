"""Descriptive position-sizing calculations for intraday planning."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSize:
    """Calculated position-sizing references."""

    risk_amount: float
    risk_per_share: float
    risk_quantity: int
    capital_quantity: int
    quantity: int
    planned_capital: float
    planned_risk: float
    planned_reward: float
    planned_rr: float | None


def _finite_number(value: float, name: str) -> float:
    """Convert an input to a finite float or raise a clear validation error."""
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def calculate_position_size(
    capital: float,
    risk_percent: float,
    entry: float,
    stop_loss: float,
    target: float,
    side: str = "LONG",
) -> PositionSize:
    """Calculate whole-share quantity subject to risk and available-capital limits.

    LONG requires stop_loss < entry < target. SHORT requires target < entry < stop_loss.
    The risk percentage is expressed in percentage points (for example, 1.0 means 1%).
    """
    capital = _finite_number(capital, "capital")
    risk_percent = _finite_number(risk_percent, "risk_percent")
    entry = _finite_number(entry, "entry")
    stop_loss = _finite_number(stop_loss, "stop_loss")
    target = _finite_number(target, "target")

    if not isinstance(side, str):
        raise ValueError("side must be LONG or SHORT")
    normalized_side = side.strip().upper()
    if normalized_side not in {"LONG", "SHORT"}:
        raise ValueError("side must be LONG or SHORT")
    if capital <= 0:
        raise ValueError("capital must be greater than zero")
    if not 0 <= risk_percent <= 100:
        raise ValueError("risk_percent must be between 0 and 100")
    if entry <= 0 or stop_loss <= 0 or target <= 0:
        raise ValueError("entry, stop_loss and target must be greater than zero")

    valid_levels = (
        stop_loss < entry < target
        if normalized_side == "LONG"
        else target < entry < stop_loss
    )
    if not valid_levels:
        raise ValueError(
            "LONG requires stop_loss < entry < target; "
            "SHORT requires target < entry < stop_loss"
        )

    risk_amount = capital * risk_percent / 100.0
    risk_per_share = abs(entry - stop_loss)
    risk_quantity = math.floor(risk_amount / risk_per_share)
    capital_quantity = math.floor(capital / entry)
    quantity = max(0, min(risk_quantity, capital_quantity))

    planned_capital = quantity * entry
    planned_risk = quantity * risk_per_share
    reward_per_share = target - entry if normalized_side == "LONG" else entry - target
    planned_reward = quantity * reward_per_share
    planned_rr = planned_reward / planned_risk if planned_risk > 0 else None

    return PositionSize(
        risk_amount=round(risk_amount, 2),
        risk_per_share=round(risk_per_share, 2),
        risk_quantity=risk_quantity,
        capital_quantity=capital_quantity,
        quantity=quantity,
        planned_capital=round(planned_capital, 2),
        planned_risk=round(planned_risk, 2),
        planned_reward=round(planned_reward, 2),
        planned_rr=round(planned_rr, 2) if planned_rr is not None else None,
    )
