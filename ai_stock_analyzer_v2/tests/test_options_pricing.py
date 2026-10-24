"""Regression tests for the Black-Scholes pricing engine."""

import math

import pytest

from engine.options_pricing import black_scholes_price_and_greeks


def test_at_the_money_call_matches_known_reference_value() -> None:
    result = black_scholes_price_and_greeks(
        spot=100,
        strike=100,
        time_to_expiry=1,
        risk_free_rate=0.05,
        volatility=0.2,
    )
    assert result.price == pytest.approx(10.4505835722, abs=1e-8)
    assert result.delta == pytest.approx(0.6368306512, abs=1e-8)
    assert result.gamma == pytest.approx(0.0187620173, abs=1e-8)
    assert result.vega == pytest.approx(37.5240347, abs=1e-6)
    assert result.theta == pytest.approx(-6.4140275, abs=1e-6)
    assert result.rho == pytest.approx(53.2324815, abs=1e-6)


def test_put_call_parity_holds_without_dividend_yield() -> None:
    call = black_scholes_price_and_greeks(
        spot=100,
        strike=105,
        time_to_expiry=0.75,
        risk_free_rate=0.06,
        volatility=0.25,
        option_type="call",
    )
    put = black_scholes_price_and_greeks(
        spot=100,
        strike=105,
        time_to_expiry=0.75,
        risk_free_rate=0.06,
        volatility=0.25,
        option_type="put",
    )
    parity = 100 - 105 * math.exp(-0.06 * 0.75)
    assert call.price - put.price == pytest.approx(parity, abs=1e-10)


def test_dividend_yield_put_call_parity() -> None:
    call = black_scholes_price_and_greeks(
        spot=100,
        strike=98,
        time_to_expiry=0.5,
        risk_free_rate=0.04,
        volatility=0.3,
        dividend_yield=0.015,
        option_type="call",
    )
    put = black_scholes_price_and_greeks(
        spot=100,
        strike=98,
        time_to_expiry=0.5,
        risk_free_rate=0.04,
        volatility=0.3,
        dividend_yield=0.015,
        option_type="put",
    )
    parity = 100 * math.exp(-0.015 * 0.5) - 98 * math.exp(-0.04 * 0.5)
    assert call.price - put.price == pytest.approx(parity, abs=1e-10)


@pytest.mark.parametrize(
    ("option_type", "expected_price", "expected_delta"),
    [("call", 20.0, 1.0), ("put", 0.0, 0.0)],
)
def test_expired_option_intrinsic_value_and_greeks(
    option_type: str, expected_price: float, expected_delta: float
) -> None:
    result = black_scholes_price_and_greeks(
        spot=120,
        strike=100,
        time_to_expiry=0,
        risk_free_rate=0.05,
        volatility=0.2,
        option_type=option_type,
    )
    assert result.price == expected_price
    assert result.delta == expected_delta
    assert result.gamma == result.vega == result.theta == result.rho == 0.0
    assert result.d1 is result.d2 is None


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"spot": 0}, "spot must be positive"),
        ({"strike": -1}, "strike must be positive"),
        ({"time_to_expiry": -0.1}, "time_to_expiry must be non-negative"),
        ({"volatility": -0.1}, "volatility must be non-negative"),
        ({"volatility": 0.0}, "volatility must be positive before expiry"),
        ({"option_type": "straddle"}, "option_type must be 'call' or 'put'"),
        ({"spot": math.inf}, "spot must be finite"),
        ({"risk_free_rate": math.nan}, "risk_free_rate must be finite"),
    ],
)
def test_invalid_inputs_are_rejected(kwargs: dict, message: str) -> None:
    inputs = {
        "spot": 100,
        "strike": 100,
        "time_to_expiry": 1,
        "risk_free_rate": 0.05,
        "volatility": 0.2,
    }
    inputs.update(kwargs)
    with pytest.raises(ValueError, match=message):
        black_scholes_price_and_greeks(**inputs)


def test_option_type_is_case_insensitive() -> None:
    result = black_scholes_price_and_greeks(
        spot=100,
        strike=100,
        time_to_expiry=1,
        risk_free_rate=0.05,
        volatility=0.2,
        option_type="PUT",
    )
    assert result.option_type == "put"
    assert result.price == pytest.approx(5.5735260223, abs=1e-8)


def test_greeks_have_expected_signs_for_standard_case() -> None:
    call = black_scholes_price_and_greeks(
        spot=100,
        strike=100,
        time_to_expiry=1,
        risk_free_rate=0.05,
        volatility=0.2,
        option_type="call",
    )
    put = black_scholes_price_and_greeks(
        spot=100,
        strike=100,
        time_to_expiry=1,
        risk_free_rate=0.05,
        volatility=0.2,
        option_type="put",
    )
    assert call.delta > 0
    assert put.delta < 0
    assert call.gamma == pytest.approx(put.gamma)
    assert call.vega == pytest.approx(put.vega)
    assert call.theta < 0
    assert call.rho > 0
    assert put.rho < 0
