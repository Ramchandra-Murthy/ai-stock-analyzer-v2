"""Position sizing rules (research helpers; they do not place orders)."""

from __future__ import annotations

import math


def _require_finite(**values: float) -> None:
    """Reject non-numeric and non-finite sizing inputs before arithmetic."""
    for name, value in values.items():
        try:
            finite = math.isfinite(value)
        except TypeError as exc:
            raise ValueError(f"{name} must be finite") from exc
        if not finite:
            raise ValueError(f"{name} must be finite")


def kelly_fraction(win_rate: float, payoff_ratio: float) -> float:
    """Kelly bet fraction f* = p - (1-p)/b, floored at 0 (never bet a negative edge)."""
    _require_finite(win_rate=win_rate, payoff_ratio=payoff_ratio)
    if not 0 < win_rate < 1 or payoff_ratio <= 0:
        raise ValueError("win_rate must be in (0, 1) and payoff_ratio positive")
    return max(win_rate - (1.0 - win_rate) / payoff_ratio, 0.0)


def fractional_kelly(
    win_rate: float, payoff_ratio: float, fraction: float = 0.25, cap: float = 0.25
) -> float:
    """A fraction of full Kelly, capped: full Kelly is very aggressive when edge is uncertain."""
    _require_finite(fraction=fraction, cap=cap)
    if not 0 < fraction <= 1 or not 0 < cap <= 1:
        raise ValueError("fraction and cap must be in (0, 1]")
    return min(kelly_fraction(win_rate, payoff_ratio) * fraction, cap)


def risk_based_quantity(
    capital: float,
    risk_pct: float,
    entry: float,
    stop: float,
    *,
    lot_size: int = 1,
    max_position_pct: float = 1.0,
) -> dict[str, float]:
    """Shares/lots such that hitting the stop loses about ``risk_pct`` of capital.

    Rounded DOWN to whole lots and limited so notional <= ``max_position_pct`` of capital.
    Gaps and slippage can make the real loss larger than the stop distance implies.
    """
    _require_finite(
        capital=capital,
        risk_pct=risk_pct,
        entry=entry,
        stop=stop,
        max_position_pct=max_position_pct,
    )
    if isinstance(lot_size, bool) or not isinstance(lot_size, int) or lot_size < 1:
        raise ValueError("lot_size must be a positive integer")
    if capital <= 0 or not 0 < risk_pct <= 0.2 or entry <= 0 or stop <= 0:
        raise ValueError(
            "capital, entry, stop must be positive; risk_pct in (0, 0.2]"
        )
    if not 0 < max_position_pct <= 1:
        raise ValueError("max_position_pct must be in (0, 1]")
    per_unit_risk = abs(entry - stop)
    if per_unit_risk == 0:
        raise ValueError("entry and stop must differ")
    by_risk = (capital * risk_pct) / per_unit_risk
    by_notional = (capital * max_position_pct) / entry
    lots = math.floor(min(by_risk, by_notional) / lot_size)
    qty = lots * lot_size
    return {
        "lots": float(lots),
        "quantity": float(qty),
        "notional": qty * entry,
        "risk_amount": qty * per_unit_risk,
        "risk_pct_of_capital": qty * per_unit_risk / capital,
        "limited_by": 0.0 if by_risk <= by_notional else 1.0,  # 0 = risk budget, 1 = notional cap
    }


def atr_stop(entry: float, atr: float, multiple: float = 2.0, long: bool = True) -> float:
    _require_finite(entry=entry, atr=atr, multiple=multiple)
    if entry <= 0 or atr <= 0 or multiple <= 0:
        raise ValueError("entry, atr and multiple must be positive")
    stop = entry - multiple * atr if long else entry + multiple * atr
    if stop <= 0:
        raise ValueError("Stop would be non-positive; use a smaller multiple.")
    return stop
