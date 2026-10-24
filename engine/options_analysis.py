"""Implied-volatility inversion and deterministic option scenario analysis."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product
from math import exp, isfinite

from engine.options_pricing import OptionPricingResult, black_scholes_price_and_greeks


@dataclass(frozen=True)
class OptionScenario:
    """One theoretical option valuation for a spot/volatility/expiry combination."""

    spot: float
    volatility: float
    time_to_expiry: float
    result: OptionPricingResult


def implied_volatility(
    *,
    spot: float,
    strike: float,
    time_to_expiry: float,
    risk_free_rate: float,
    market_price: float,
    option_type: str = "call",
    dividend_yield: float = 0.0,
    tolerance: float = 1e-8,
    max_iterations: int = 200,
    max_volatility: float = 10.0,
) -> float:
    """Solve Black-Scholes implied volatility with a bounded bisection search.

    The supplied market_price must be an observed premium supplied by the caller;
    this function never fetches or invents market data. Volatility and rates are
    annualized decimals. Raises ValueError for invalid or infeasible inputs and
    RuntimeError if the configured search does not converge.
    """
    values = {
        "spot": spot,
        "strike": strike,
        "time_to_expiry": time_to_expiry,
        "risk_free_rate": risk_free_rate,
        "market_price": market_price,
        "dividend_yield": dividend_yield,
        "tolerance": tolerance,
        "max_volatility": max_volatility,
    }
    for name, value in values.items():
        if not isfinite(value):
            raise ValueError(f"{name} must be finite")

    if spot <= 0:
        raise ValueError("spot must be positive")
    if strike <= 0:
        raise ValueError("strike must be positive")
    if time_to_expiry <= 0:
        raise ValueError("time_to_expiry must be positive to solve implied volatility")
    if market_price < 0:
        raise ValueError("market_price must be non-negative")
    if tolerance <= 0:
        raise ValueError("tolerance must be positive")
    if (
        isinstance(max_iterations, bool)
        or not isinstance(max_iterations, int)
        or max_iterations < 1
    ):
        raise ValueError("max_iterations must be a positive integer")
    if max_volatility <= 0:
        raise ValueError("max_volatility must be positive")

    normalized_type = option_type.strip().lower()
    if normalized_type not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'")

    discounted_spot = spot * exp(-dividend_yield * time_to_expiry)
    discounted_strike = strike * exp(-risk_free_rate * time_to_expiry)
    if normalized_type == "call":
        lower_bound = max(discounted_spot - discounted_strike, 0.0)
        upper_bound = discounted_spot
    else:
        lower_bound = max(discounted_strike - discounted_spot, 0.0)
        upper_bound = discounted_strike

    if market_price < lower_bound - tolerance:
        raise ValueError("market_price is below the no-arbitrage lower bound")
    if market_price > upper_bound + tolerance:
        raise ValueError("market_price is above the no-arbitrage upper bound")
    if market_price <= lower_bound + tolerance:
        return 0.0
    if market_price >= upper_bound - tolerance:
        raise ValueError("market_price is at the upper bound; no finite implied volatility exists")

    def model_price(volatility: float) -> float:
        return black_scholes_price_and_greeks(
            spot=spot,
            strike=strike,
            time_to_expiry=time_to_expiry,
            risk_free_rate=risk_free_rate,
            volatility=volatility,
            option_type=normalized_type,
            dividend_yield=dividend_yield,
        ).price

    low = min(1e-8, max_volatility / 2.0)
    high = max_volatility
    if model_price(high) < market_price:
        raise ValueError("market_price cannot be bracketed by max_volatility")

    for _ in range(max_iterations):
        middle = (low + high) / 2.0
        price = model_price(middle)
        difference = price - market_price
        if abs(difference) <= tolerance:
            return middle
        if difference < 0:
            low = middle
        else:
            high = middle

    estimate = (low + high) / 2.0
    if abs(model_price(estimate) - market_price) <= tolerance:
        return estimate
    raise RuntimeError("implied-volatility search did not converge within max_iterations")


def option_price_scenarios(
    *,
    spot_scenarios: Sequence[float],
    volatility_scenarios: Sequence[float],
    time_to_expiry_scenarios: Sequence[float],
    strike: float,
    risk_free_rate: float,
    option_type: str = "call",
    dividend_yield: float = 0.0,
) -> tuple[OptionScenario, ...]:
    """Value the Cartesian product of explicit spot, volatility and time scenarios.

    Scenario values are supplied by the caller; this function does not forecast
    prices or produce trading recommendations. A zero volatility is valid only
    at expiry, following the pricing engine's input conventions.
    """
    scenario_inputs = {
        "spot_scenarios": spot_scenarios,
        "volatility_scenarios": volatility_scenarios,
        "time_to_expiry_scenarios": time_to_expiry_scenarios,
    }
    for name, values in scenario_inputs.items():
        if not values:
            raise ValueError(f"{name} must contain at least one value")

    results = []
    for spot, volatility, time_to_expiry in product(
        spot_scenarios, volatility_scenarios, time_to_expiry_scenarios
    ):
        result = black_scholes_price_and_greeks(
            spot=spot,
            strike=strike,
            time_to_expiry=time_to_expiry,
            risk_free_rate=risk_free_rate,
            volatility=volatility,
            option_type=option_type,
            dividend_yield=dividend_yield,
        )
        results.append(
            OptionScenario(
                spot=spot,
                volatility=volatility,
                time_to_expiry=time_to_expiry,
                result=result,
            )
        )
    return tuple(results)
