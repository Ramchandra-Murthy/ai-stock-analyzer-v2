"""Risk controls and capital allocation for AI paper trading."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Integral, Real


def _require_finite_number(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(float(value)):
        raise ValueError(f"{name} must be a finite number")


@dataclass(frozen=True)
class RiskLimits:
    """Portfolio-level limits applied before simulated AI paper orders."""

    max_exposure_pct: float = 80.0
    max_position_pct: float = 20.0
    cash_reserve_pct: float = 10.0

    def __post_init__(self) -> None:
        _require_finite_number("max_exposure_pct", self.max_exposure_pct)
        _require_finite_number("max_position_pct", self.max_position_pct)
        _require_finite_number("cash_reserve_pct", self.cash_reserve_pct)
        if not 0.0 < self.max_exposure_pct <= 100.0:
            raise ValueError("max_exposure_pct must be between 0 and 100")
        if not 0.0 < self.max_position_pct <= 100.0:
            raise ValueError("max_position_pct must be between 0 and 100")
        if not 0.0 <= self.cash_reserve_pct < 100.0:
            raise ValueError("cash_reserve_pct must be between 0 and 100")
        if self.max_position_pct > self.max_exposure_pct:
            raise ValueError("max_position_pct cannot exceed max_exposure_pct")

    def allocation(
        self,
        equity: float,
        cash: float,
        market_value: float,
        candidate_count: int,
    ) -> dict[str, float]:
        """Return total capital available and per-candidate allocation."""
        _require_finite_number("equity", equity)
        _require_finite_number("cash", cash)
        _require_finite_number("market_value", market_value)
        if equity <= 0:
            raise ValueError("equity must be positive")
        if cash < 0 or market_value < 0:
            raise ValueError("cash and market_value cannot be negative")
        if isinstance(candidate_count, bool) or not isinstance(candidate_count, Integral):
            raise ValueError("candidate_count must be a non-negative integer")
        if candidate_count < 0:
            raise ValueError("candidate_count must be a non-negative integer")

        max_exposure_value = equity * self.max_exposure_pct / 100.0
        reserve_value = equity * self.cash_reserve_pct / 100.0
        exposure_room = max(0.0, max_exposure_value - market_value)
        cash_room = max(0.0, cash - reserve_value)
        total_available = min(exposure_room, cash_room)

        if candidate_count == 0:
            per_candidate = 0.0
        else:
            # Divide the portfolio budget across all candidates before applying
            # the single-position cap; otherwise aggregate allocations can exceed
            # the available capital when several candidates are selected.
            candidate_budget = total_available / candidate_count
            per_candidate = min(
                equity * self.max_position_pct / 100.0,
                candidate_budget,
            )

        return {
            "total_available": total_available,
            "per_candidate": per_candidate,
            "max_exposure_value": max_exposure_value,
            "reserve_value": reserve_value,
        }


def risk_warnings(
    equity: float,
    cash: float,
    market_value: float,
    limits: RiskLimits,
) -> list[str]:
    """Return human-readable warnings for the current portfolio state."""
    _require_finite_number("equity", equity)
    _require_finite_number("cash", cash)
    _require_finite_number("market_value", market_value)
    if cash < 0 or market_value < 0:
        raise ValueError("cash and market_value cannot be negative")
    if equity <= 0:
        return ["Portfolio equity is non-positive. No new allocation is allowed."]

    warnings: list[str] = []
    exposure_pct = market_value / equity * 100.0
    cash_pct = cash / equity * 100.0

    if exposure_pct > limits.max_exposure_pct:
        warnings.append(
            f"Exposure is {exposure_pct:.1f}%, above the " f"{limits.max_exposure_pct:.1f}% limit."
        )
    if cash_pct < limits.cash_reserve_pct:
        warnings.append(
            f"Cash reserve is {cash_pct:.1f}%, below the "
            f"{limits.cash_reserve_pct:.1f}% minimum."
        )
    return warnings
