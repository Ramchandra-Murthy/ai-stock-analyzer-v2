"""Combine observed option premiums with theoretical pricing and scenarios."""

from __future__ import annotations

from dataclasses import dataclass

from engine.options_analysis import OptionScenario, implied_volatility, option_price_scenarios
from engine.options_pricing import OptionPricingResult, black_scholes_price_and_greeks


@dataclass(frozen=True)
class OptionPricingSnapshot:
    """IV inferred from an observed premium plus an assumption-based model and scenarios."""

    observed_premium: float
    implied_volatility: float
    model_result: OptionPricingResult
    scenarios: tuple[OptionScenario, ...]


def analyze_observed_option(
    *,
    spot: float,
    strike: float,
    time_to_expiry: float,
    risk_free_rate: float,
    observed_premium: float,
    model_volatility: float,
    option_type: str = "call",
    dividend_yield: float = 0.0,
    spot_shift: float = 0.01,
    volatility_shift: float = 0.05,
) -> OptionPricingSnapshot:
    """Calculate IV, an assumption-based theoretical value, Greeks, and scenarios.

    The observed premium must come from the caller's verified market-data source.
    The model value uses model_volatility, while implied volatility is inferred
    separately from observed_premium. Rates, volatility and time are annualized
    decimals/years. This function does not fetch data or generate trade signals.
    """
    if observed_premium < 0:
        raise ValueError("observed_premium must be non-negative")
    if model_volatility <= 0:
        raise ValueError("model_volatility must be positive")
    if not 0 <= spot_shift < 1:
        raise ValueError("spot_shift must be in [0, 1)")
    if volatility_shift < 0:
        raise ValueError("volatility_shift must be non-negative")

    iv = implied_volatility(
        spot=spot,
        strike=strike,
        time_to_expiry=time_to_expiry,
        risk_free_rate=risk_free_rate,
        market_price=observed_premium,
        option_type=option_type,
        dividend_yield=dividend_yield,
    )
    model_result = black_scholes_price_and_greeks(
        spot=spot,
        strike=strike,
        time_to_expiry=time_to_expiry,
        risk_free_rate=risk_free_rate,
        volatility=model_volatility,
        option_type=option_type,
        dividend_yield=dividend_yield,
    )
    scenarios = option_price_scenarios(
        spot_scenarios=(spot * (1.0 - spot_shift), spot, spot * (1.0 + spot_shift)),
        volatility_scenarios=(
            max(0.001, model_volatility - volatility_shift),
            model_volatility,
            model_volatility + volatility_shift,
        ),
        time_to_expiry_scenarios=(time_to_expiry, max(time_to_expiry / 2.0, 1e-8)),
        strike=strike,
        risk_free_rate=risk_free_rate,
        option_type=option_type,
        dividend_yield=dividend_yield,
    )
    return OptionPricingSnapshot(
        observed_premium=observed_premium,
        implied_volatility=iv,
        model_result=model_result,
        scenarios=tuple(scenarios),
    )
