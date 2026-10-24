"""Tests for implied-volatility inversion and option scenario analysis."""

import pytest

from engine.options_analysis import implied_volatility, option_price_scenarios
from engine.options_pricing import black_scholes_price_and_greeks


@pytest.mark.parametrize("option_type", ["call", "put"])
def test_implied_volatility_recovers_input_volatility(option_type: str) -> None:
    observed = black_scholes_price_and_greeks(
        spot=100,
        strike=105,
        time_to_expiry=0.75,
        risk_free_rate=0.04,
        volatility=0.32,
        option_type=option_type,
        dividend_yield=0.01,
    ).price

    estimate = implied_volatility(
        spot=100,
        strike=105,
        time_to_expiry=0.75,
        risk_free_rate=0.04,
        market_price=observed,
        option_type=option_type,
        dividend_yield=0.01,
    )

    assert estimate == pytest.approx(0.32, abs=1e-6)


def test_implied_volatility_returns_zero_at_lower_bound() -> None:
    estimate = implied_volatility(
        spot=100,
        strike=120,
        time_to_expiry=0.5,
        risk_free_rate=0.03,
        market_price=0.0,
        option_type="call",
    )
    assert estimate == 0.0


@pytest.mark.parametrize(
    ("market_price", "message"),
    [
        (-1.0, "market_price must be non-negative"),
        (110.0, "market_price is above the no-arbitrage upper bound"),
    ],
)
def test_implied_volatility_rejects_infeasible_prices(market_price: float, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        implied_volatility(
            spot=100,
            strike=100,
            time_to_expiry=1,
            risk_free_rate=0.05,
            market_price=market_price,
        )


def test_implied_volatility_rejects_expired_contract() -> None:
    with pytest.raises(ValueError, match="time_to_expiry must be positive"):
        implied_volatility(
            spot=100,
            strike=100,
            time_to_expiry=0,
            risk_free_rate=0.05,
            market_price=5,
        )


def test_implied_volatility_rejects_unbracketed_price() -> None:
    with pytest.raises(ValueError, match="cannot be bracketed"):
        implied_volatility(
            spot=100,
            strike=100,
            time_to_expiry=1,
            risk_free_rate=0.05,
            market_price=99,
            max_volatility=0.01,
        )


def test_scenario_analysis_returns_full_cartesian_product() -> None:
    scenarios = option_price_scenarios(
        spot_scenarios=(95.0, 100.0, 105.0),
        volatility_scenarios=(0.2, 0.3),
        time_to_expiry_scenarios=(0.25, 0.5),
        strike=100,
        risk_free_rate=0.05,
        option_type="call",
    )

    assert len(scenarios) == 12
    assert all(scenario.result.price >= 0 for scenario in scenarios)
    assert len({scenario.result.price for scenario in scenarios}) > 1


def test_scenario_analysis_rejects_empty_dimension() -> None:
    with pytest.raises(ValueError, match="spot_scenarios must contain"):
        option_price_scenarios(
            spot_scenarios=(),
            volatility_scenarios=(0.2,),
            time_to_expiry_scenarios=(0.5,),
            strike=100,
            risk_free_rate=0.05,
        )


def test_scenario_analysis_propagates_invalid_scenario_inputs() -> None:
    with pytest.raises(ValueError, match="spot must be positive"):
        option_price_scenarios(
            spot_scenarios=(0.0,),
            volatility_scenarios=(0.2,),
            time_to_expiry_scenarios=(0.5,),
            strike=100,
            risk_free_rate=0.05,
        )
