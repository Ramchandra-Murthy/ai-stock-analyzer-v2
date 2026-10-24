"""Tests for historical option-pricing validation metrics."""

import math

import pytest

from engine.options_validation import (
    PricingObservation,
    calculate_pricing_validation_metrics,
)


def observation(observed: float, theoretical: float, **kwargs: str) -> PricingObservation:
    return PricingObservation(
        observed_price=observed,
        theoretical_price=theoretical,
        option_type=kwargs.get("option_type", "call"),
        expiry=kwargs.get("expiry", "2026-11-26"),
        contract_id=kwargs.get("contract_id", ""),
        moneyness=kwargs.get("moneyness", "ATM"),
        timestamp=kwargs.get("timestamp", ""),
    )


def test_validation_metrics_calculate_mae_rmse_and_bias() -> None:
    result = calculate_pricing_validation_metrics([observation(10, 12), observation(20, 17)])

    assert result.observation_count == 2
    assert result.mean_absolute_error == pytest.approx(2.5)
    assert result.root_mean_squared_error == pytest.approx(math.sqrt(6.5))
    assert result.mean_error_bias == pytest.approx(-0.5)


def test_perfect_prices_have_zero_error() -> None:
    result = calculate_pricing_validation_metrics([observation(10, 10)])
    assert result.mean_absolute_error == 0
    assert result.root_mean_squared_error == 0
    assert result.mean_error_bias == 0


@pytest.mark.parametrize(
    ("record", "message"),
    [
        (observation(-1, 2), "observed_price must be non-negative"),
        (observation(1, -2), "theoretical_price must be non-negative"),
        (observation(float("nan"), 2), "observed_price must be finite"),
        (observation(1, float("inf")), "theoretical_price must be finite"),
        (observation(1, 2, option_type="straddle"), "option_type must be"),
        (observation(1, 2, expiry=""), "expiry must be non-empty"),
    ],
)
def test_invalid_observations_are_rejected(record: PricingObservation, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        calculate_pricing_validation_metrics([record])


def test_empty_observations_are_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        calculate_pricing_validation_metrics([])


def test_duplicate_timestamp_and_contract_is_rejected() -> None:
    timestamp = "2026-10-14T10:00:00+05:30"
    first = observation(10, 11, timestamp=timestamp, contract_id="NIFTY-26000-CE")
    second = observation(10.5, 11.5, timestamp=timestamp, contract_id="NIFTY-26000-CE")
    with pytest.raises(ValueError, match="duplicate observation key"):
        calculate_pricing_validation_metrics([first, second])


def test_different_contracts_at_same_timestamp_are_allowed() -> None:
    timestamp = "2026-10-14T10:00:00+05:30"
    first = observation(10, 11, timestamp=timestamp, contract_id="NIFTY-26000-CE")
    second = observation(10, 11, timestamp=timestamp, contract_id="NIFTY-26100-CE")
    assert calculate_pricing_validation_metrics([first, second]).observation_count == 2
