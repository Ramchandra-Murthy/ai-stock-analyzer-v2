"""Tests for the NIFTY Options Book V2 data model."""

from datetime import date

import pytest

from strategy.nifty_options_v2 import NiftyCallContract, NiftyCallObservation


def test_call_contract_requires_positive_strike() -> None:
    with pytest.raises(ValueError, match="strike must be positive"):
        NiftyCallContract(expiry=date(2026, 10, 29), strike=0)


def test_call_observation_identifies_itm_call() -> None:
    observation = NiftyCallObservation(
        contract=NiftyCallContract(expiry=date(2026, 10, 29), strike=25000),
        observed_date=date(2026, 10, 1),
        spot=25500,
        ltp=600,
    )

    assert observation.is_itm is True


def test_call_observation_rejects_invalid_market_values() -> None:
    contract = NiftyCallContract(expiry=date(2026, 10, 29), strike=25000)

    with pytest.raises(ValueError, match="spot must be positive"):
        NiftyCallObservation(
            contract=contract,
            observed_date=date(2026, 10, 1),
            spot=0,
            ltp=600,
        )

    with pytest.raises(ValueError, match="ltp must be non-negative"):
        NiftyCallObservation(
            contract=contract,
            observed_date=date(2026, 10, 1),
            spot=25500,
            ltp=-1,
        )
