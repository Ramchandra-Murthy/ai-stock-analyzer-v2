"""Descriptive position-sizing calculations for intraday planning."""

# fmt: off

from __future__ import annotations

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


def calculate_position_size(
    capital: float,
    risk_percent: float,
    entry: float,
    stop_loss: float,
    target: float,
    side: str = "LONG",
) -> PositionSize:
    """Calculate a capped quantity from risk and capital constraints."""
    capital = max(0.0, float(capital))
    risk_percent = max(0.0, float(risk_percent))
    entry = float(entry)
    stop_loss = float(stop_loss)
    target = float(target)
    normalized_side = side.upper()

    risk_amount = capital * risk_percent / 100.0
    risk_per_share = abs(entry - stop_loss)
    risk_quantity = int(risk_amount // risk_per_share) if risk_per_share > 0 else 0
    capital_quantity = int(capital // entry) if entry > 0 else 0
    quantity = max(0, min(risk_quantity, capital_quantity))

    planned_capital = quantity * entry
    planned_risk = quantity * risk_per_share
    reward_per_share = (
        target - entry if normalized_side == "LONG" else entry - target
    )
    planned_reward = max(0.0, quantity * reward_per_share)
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

# fmt: on
