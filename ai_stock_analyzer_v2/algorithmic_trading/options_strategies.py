"""Option strategy payoff, breakevens and Greeks (analysis only; no orders, no margin).

Payoff at expiry is piecewise linear in the underlying, so maxima, minima and breakevens are
computed exactly from the strike kinks instead of from a sampled grid. Premiums are per unit
of the underlying; multiply by lot size and number of lots for rupees. Margin requirements for
short options are NOT computed here: they are set by the exchange/broker and can be large.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from engine.options_pricing import black_scholes_price_and_greeks

DEFAULT_NIFTY_LOT_SIZE = 65  # NSE revision effective Jan 2026; re-check with NSE before use
TEMPLATES = (
    "Long straddle",
    "Short straddle",
    "Long strangle",
    "Short strangle",
    "Bull call spread",
    "Bear put spread",
    "Iron condor",
)


@dataclass(frozen=True)
class Leg:
    kind: str  # "call" or "put"
    strike: float
    premium: float  # per unit, paid (long) or received (short)
    qty: int  # +1 long, -1 short (multiples allowed)

    def __post_init__(self) -> None:
        if self.kind not in ("call", "put"):
            raise ValueError("kind must be 'call' or 'put'")
        if self.strike <= 0 or self.premium < 0 or self.qty == 0:
            raise ValueError("strike must be positive, premium non-negative, qty non-zero")


def leg_payoff(leg: Leg, spot: np.ndarray | float) -> np.ndarray | float:
    intrinsic = (
        np.maximum(spot - leg.strike, 0.0)
        if leg.kind == "call"
        else np.maximum(leg.strike - spot, 0.0)
    )
    return leg.qty * (intrinsic - leg.premium)


def expiry_payoff(legs: list[Leg], spots: np.ndarray | float) -> np.ndarray | float:
    """Profit/loss per unit at expiry, net of premiums."""
    if not legs:
        raise ValueError("A strategy needs at least one leg.")
    return sum(leg_payoff(leg, spots) for leg in legs)


def net_premium(legs: list[Leg]) -> float:
    """Positive = net debit paid per unit; negative = net credit received."""
    return float(sum(leg.qty * leg.premium for leg in legs))


def _slope_up(legs: list[Leg]) -> float:
    return float(sum(leg.qty for leg in legs if leg.kind == "call"))


def payoff_summary(legs: list[Leg]) -> dict[str, float | None | list[float]]:
    """Max profit, max loss (None = unbounded) and exact breakevens, per unit."""
    strikes = sorted({leg.strike for leg in legs})
    points = np.array([0.0, *strikes])
    values = np.asarray(expiry_payoff(legs, points), dtype=float)
    slope = _slope_up(legs)

    breakevens: list[float] = []
    for i in range(len(points) - 1):
        a, b, va, vb = points[i], points[i + 1], values[i], values[i + 1]
        if va == 0 and a > 0:
            breakevens.append(float(a))
        if va * vb < 0:
            breakevens.append(float(a + (b - a) * (0 - va) / (vb - va)))
    last_k, last_v = points[-1], values[-1]
    if last_v == 0 and last_k > 0 and last_k not in breakevens:
        breakevens.append(float(last_k))
    if slope != 0 and last_v * slope < 0:
        breakevens.append(float(last_k - last_v / slope))
    breakevens = sorted({round(x, 6) for x in breakevens})

    best, worst = float(values.max()), float(values.min())
    return {
        "max_profit": None if slope > 0 else best,
        "max_loss": None if slope < 0 else -worst if worst < 0 else 0.0,
        "breakevens": breakevens,
        "net_premium": net_premium(legs),
    }


def aggregate_greeks(
    legs: list[Leg], *, spot: float, days_to_expiry: float, rate: float, vol: float
) -> dict[str, float]:
    """Position Greeks per unit of the underlying (Black-Scholes, one volatility for all legs).

    Vega is per 1 vol point (0.01), theta per calendar day.
    """
    t = max(days_to_expiry, 0.0) / 365.0
    total = dict.fromkeys(("delta", "gamma", "vega", "theta"), 0.0)
    for leg in legs:
        g = black_scholes_price_and_greeks(
            spot=spot,
            strike=leg.strike,
            time_to_expiry=t,
            risk_free_rate=rate,
            volatility=vol,
            option_type=leg.kind,
        )
        total["delta"] += leg.qty * g.delta
        total["gamma"] += leg.qty * g.gamma
        total["vega"] += leg.qty * g.vega / 100.0
        total["theta"] += leg.qty * g.theta / 365.0
    return total


def theoretical_premium(
    kind: str, strike: float, *, spot: float, days_to_expiry: float, rate: float, vol: float
) -> float:
    t = max(days_to_expiry, 0.0) / 365.0
    return black_scholes_price_and_greeks(
        spot=spot,
        strike=strike,
        time_to_expiry=t,
        risk_free_rate=rate,
        volatility=vol,
        option_type=kind,
    ).price


def build_template(
    name: str,
    *,
    spot: float,
    strike_step: float,
    width_steps: int,
    days_to_expiry: float,
    rate: float,
    vol: float,
    premium_lookup: dict[tuple[str, float], float] | None = None,
) -> list[Leg]:
    """Legs for a named template around the at-the-money strike.

    Premiums come from ``premium_lookup`` (e.g. last traded prices from a live chain) when a
    strike is present, otherwise from Black-Scholes at ``vol``.
    """
    if name not in TEMPLATES:
        raise ValueError(f"Unknown template: {name}")
    if strike_step <= 0 or width_steps < 1 or spot <= 0:
        raise ValueError("strike_step and spot must be positive and width_steps at least 1")
    atm = round(spot / strike_step) * strike_step
    w = width_steps * strike_step

    def leg(kind: str, strike: float, qty: int) -> Leg:
        if strike <= 0:
            raise ValueError("Strike would be non-positive; reduce the width.")
        premium = (premium_lookup or {}).get((kind, strike))
        if premium is None or not math.isfinite(premium) or premium <= 0:
            premium = theoretical_premium(
                kind, strike, spot=spot, days_to_expiry=days_to_expiry, rate=rate, vol=vol
            )
        return Leg(kind, strike, float(premium), qty)

    table = {
        "Long straddle": [("call", atm, 1), ("put", atm, 1)],
        "Short straddle": [("call", atm, -1), ("put", atm, -1)],
        "Long strangle": [("call", atm + w, 1), ("put", atm - w, 1)],
        "Short strangle": [("call", atm + w, -1), ("put", atm - w, -1)],
        "Bull call spread": [("call", atm, 1), ("call", atm + w, -1)],
        "Bear put spread": [("put", atm, 1), ("put", atm - w, -1)],
        "Iron condor": [
            ("put", atm - 2 * w, 1),
            ("put", atm - w, -1),
            ("call", atm + w, -1),
            ("call", atm + 2 * w, 1),
        ],
    }
    return [leg(k, s, q) for k, s, q in table[name]]


def iv_rank_percentile(history: pd.Series, current: float | None = None) -> dict[str, float]:
    """IV rank (position in the 52-week range) and percentile (share of days below current)."""
    values = pd.to_numeric(history, errors="coerce").dropna().tail(252)
    if len(values) < 30:
        raise ValueError("At least 30 volatility observations are needed.")
    now = float(values.iloc[-1] if current is None else current)
    lo, hi = float(values.min()), float(values.max())
    rank = 0.0 if hi == lo else (now - lo) / (hi - lo)
    return {
        "current": now,
        "rank": float(min(max(rank, 0.0), 1.0)),
        "percentile": float((values < now).mean()),
        "low": lo,
        "high": hi,
    }
