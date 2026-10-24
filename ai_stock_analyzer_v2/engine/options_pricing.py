"""European option pricing and Greeks using the Black-Scholes-Merton model.

This deterministic calculation layer does not fetch market data, infer missing
prices, create trading signals, or submit broker orders. Rates and volatility
are annualized decimals; time to expiry is measured in years. Vega and rho are
sensitivities to a 1.00 change in volatility and rate; theta is per year.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, isfinite, log, pi, sqrt


@dataclass(frozen=True)
class OptionPricingResult:
    """Theoretical European option value and model sensitivities."""

    option_type: str
    price: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float
    d1: float | None
    d2: float | None


def _normal_cdf(value: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def _normal_pdf(value: float) -> float:
    """Standard normal probability density function."""
    return exp(-0.5 * value * value) / sqrt(2.0 * pi)


def black_scholes_price_and_greeks(
    *,
    spot: float,
    strike: float,
    time_to_expiry: float,
    risk_free_rate: float,
    volatility: float,
    option_type: str = "call",
    dividend_yield: float = 0.0,
) -> OptionPricingResult:
    """Price a European call or put and calculate its Black-Scholes Greeks.

    Inputs for rates and volatility are annualized decimals (0.05 means 5%).
    Assumes European exercise, constant rates and volatility, and continuous
    dividend yield. The result is theoretical, not an observed premium or signal.
    At expiry, Greeks use a documented intrinsic-value convention.
    """
    numeric_inputs = {
        "spot": spot,
        "strike": strike,
        "time_to_expiry": time_to_expiry,
        "risk_free_rate": risk_free_rate,
        "volatility": volatility,
        "dividend_yield": dividend_yield,
    }
    for name, value in numeric_inputs.items():
        if not isfinite(value):
            raise ValueError(f"{name} must be finite")

    if spot <= 0:
        raise ValueError("spot must be positive")
    if strike <= 0:
        raise ValueError("strike must be positive")
    if time_to_expiry < 0:
        raise ValueError("time_to_expiry must be non-negative")
    if volatility < 0:
        raise ValueError("volatility must be non-negative")

    normalized_type = option_type.strip().lower()
    if normalized_type not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'")

    if time_to_expiry == 0:
        if normalized_type == "call":
            price = max(spot - strike, 0.0)
            delta = 1.0 if spot > strike else 0.0 if spot < strike else 0.5
        else:
            price = max(strike - spot, 0.0)
            delta = -1.0 if spot < strike else 0.0 if spot > strike else -0.5
        return OptionPricingResult(
            option_type=normalized_type,
            price=price,
            delta=delta,
            gamma=0.0,
            vega=0.0,
            theta=0.0,
            rho=0.0,
            d1=None,
            d2=None,
        )

    if volatility == 0:
        raise ValueError("volatility must be positive before expiry")

    sqrt_time = sqrt(time_to_expiry)
    discounted_spot = spot * exp(-dividend_yield * time_to_expiry)
    discounted_strike = strike * exp(-risk_free_rate * time_to_expiry)
    d1 = (
        log(spot / strike)
        + (risk_free_rate - dividend_yield + 0.5 * volatility**2) * time_to_expiry
    ) / (volatility * sqrt_time)
    d2 = d1 - volatility * sqrt_time
    pdf_d1 = _normal_pdf(d1)

    gamma = exp(-dividend_yield * time_to_expiry) * pdf_d1 / (spot * volatility * sqrt_time)
    vega = discounted_spot * pdf_d1 * sqrt_time

    if normalized_type == "call":
        price = discounted_spot * _normal_cdf(d1) - discounted_strike * _normal_cdf(d2)
        delta = exp(-dividend_yield * time_to_expiry) * _normal_cdf(d1)
        theta = (
            -discounted_spot * pdf_d1 * volatility / (2.0 * sqrt_time)
            - risk_free_rate * discounted_strike * _normal_cdf(d2)
            + dividend_yield * discounted_spot * _normal_cdf(d1)
        )
        rho = strike * time_to_expiry * exp(-risk_free_rate * time_to_expiry) * _normal_cdf(d2)
    else:
        price = discounted_strike * _normal_cdf(-d2) - discounted_spot * _normal_cdf(-d1)
        delta = exp(-dividend_yield * time_to_expiry) * (_normal_cdf(d1) - 1.0)
        theta = (
            -discounted_spot * pdf_d1 * volatility / (2.0 * sqrt_time)
            + risk_free_rate * discounted_strike * _normal_cdf(-d2)
            - dividend_yield * discounted_spot * _normal_cdf(-d1)
        )
        rho = -strike * time_to_expiry * exp(-risk_free_rate * time_to_expiry) * _normal_cdf(-d2)

    return OptionPricingResult(
        option_type=normalized_type,
        price=max(price, 0.0),
        delta=delta,
        gamma=gamma,
        vega=vega,
        theta=theta,
        rho=rho,
        d1=d1,
        d2=d2,
    )
