"""Tests for the NIFTY option pricing analytics integration helper."""

import pytest

from engine.nifty_options_pricing_analytics import analyze_observed_option
from engine.options_pricing import black_scholes_price_and_greeks


def test_snapshot_recovers_implied_volatility_and_returns_scenarios() -> None:
    observed = black_scholes_price_and_greeks(
        spot=25000,
        strike=25000,
        time_to_expiry=30 / 365,
        risk_free_rate=0.06,
        volatility=0.22,
        option_type="call",
    ).price

    snapshot = analyze_observed_option(
        spot=25000,
        strike=25000,
        time_to_expiry=30 / 365,
        risk_free_rate=0.06,
        observed_premium=observed,
        model_volatility=0.20,
        option_type="call",
    )

    assert snapshot.observed_premium == pytest.approx(observed)
    assert snapshot.implied_volatility == pytest.approx(0.22, abs=1e-6)
    assert snapshot.model_result.price > 0
    assert len(snapshot.scenarios) == 18


def test_snapshot_keeps_model_volatility_separate_from_implied_volatility() -> None:
    observed = black_scholes_price_and_greeks(
        spot=25000,
        strike=25000,
        time_to_expiry=30 / 365,
        risk_free_rate=0.06,
        volatility=0.30,
        option_type="put",
    ).price

    snapshot = analyze_observed_option(
        spot=25000,
        strike=25000,
        time_to_expiry=30 / 365,
        risk_free_rate=0.06,
        observed_premium=observed,
        model_volatility=0.20,
        option_type="put",
    )

    assert snapshot.implied_volatility == pytest.approx(0.30, abs=1e-6)
    assert snapshot.model_result.price != pytest.approx(snapshot.observed_premium)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"observed_premium": -1.0}, "observed_premium must be non-negative"),
        ({"model_volatility": 0.0}, "model_volatility must be positive"),
        ({"spot_shift": 1.0}, "spot_shift must be in"),
        ({"volatility_shift": -0.01}, "volatility_shift must be non-negative"),
    ],
)
def test_snapshot_rejects_invalid_inputs(overrides: dict, message: str) -> None:
    inputs = {
        "spot": 25000.0,
        "strike": 25000.0,
        "time_to_expiry": 30 / 365,
        "risk_free_rate": 0.06,
        "observed_premium": 500.0,
        "model_volatility": 0.20,
        "option_type": "call",
    }
    inputs.update(overrides)

    with pytest.raises(ValueError, match=message):
        analyze_observed_option(**inputs)
