from datetime import date

import pandas as pd

from engine.nifty_options_v2_auto import NiftyOptionsV2AutoPaper, PaperAction
from engine.nifty_options_v2_auto_cycle import NiftyOptionsV2AutoCycle
from engine.nifty_options_v2_live import LivePaperObservation
from engine.nifty_options_v2_market_data import NiftyV2MarketObservation, select_deepest_itm_call
from strategy.nifty_options_v2 import NiftyCallContract


def test_auto_paper_handles_no_active_trade() -> None:
    observation = NiftyV2MarketObservation(
        contract=NiftyCallContract(expiry=date(2026, 10, 29), strike=24000),
        observation=LivePaperObservation(
            observed_date=date(2026, 10, 20),
            spot=25000,
            ltp=1000,
        ),
    )

    decision = NiftyOptionsV2AutoPaper().process(
        observation=observation,
        current_series_expiry=date(2026, 10, 29),
    )

    assert decision.action is PaperAction.HOLD


EXPIRIES = ("2026-10-29", "2026-11-26")


def _observation(
    *,
    observed_date: date,
    expiry: date,
) -> NiftyV2MarketObservation:
    return NiftyV2MarketObservation(
        contract=NiftyCallContract(expiry=expiry, strike=24000),
        observation=LivePaperObservation(
            observed_date=observed_date,
            spot=25000,
            ltp=1000,
        ),
    )


def test_coordinator_returns_hold_before_expiry() -> None:
    result = NiftyOptionsV2AutoCycle().process(
        expiries=EXPIRIES,
        observed_date=date(2026, 10, 20),
        observation=_observation(
            observed_date=date(2026, 10, 20),
            expiry=date(2026, 11, 26),
        ),
    )

    assert result is not None
    assert result.action is PaperAction.HOLD
    assert result.current_expiry == date(2026, 10, 29)
    assert result.next_expiry == date(2026, 11, 26)


def test_coordinator_enters_next_series_on_expiry() -> None:
    result = NiftyOptionsV2AutoCycle().process(
        expiries=EXPIRIES,
        observed_date=date(2026, 10, 29),
        observation=_observation(
            observed_date=date(2026, 10, 29),
            expiry=date(2026, 11, 26),
        ),
    )

    assert result is not None
    assert result.action is PaperAction.ENTER_NEXT_SERIES


def test_coordinator_returns_none_without_two_expiries() -> None:
    result = NiftyOptionsV2AutoCycle().process(
        expiries=("2026-10-29",),
        observed_date=date(2026, 10, 20),
        observation=_observation(
            observed_date=date(2026, 10, 20),
            expiry=date(2026, 11, 26),
        ),
    )

    assert result is None


def test_coordinator_result_records_market_observation() -> None:
    result = NiftyOptionsV2AutoCycle().process(
        expiries=EXPIRIES,
        observed_date=date(2026, 10, 29),
        observation=_observation(
            observed_date=date(2026, 10, 29),
            expiry=date(2026, 11, 26),
        ),
    )

    assert result is not None
    assert result.observed_date == date(2026, 10, 29)
    assert result.strike == 24000
    assert result.spot == 25000
    assert result.ltp == 1000


def test_end_to_end_selects_deepest_itm_and_enters_next_series() -> None:
    chain = pd.DataFrame(
        {
            "strike": [25200, 24500, 24000, 23500],
            "CE LTP": [700, 1000, 1200, 1500],
        }
    )
    observation = select_deepest_itm_call(
        chain,
        spot=25000,
        expiry=date(2026, 11, 26),
        observed_date=date(2026, 10, 29),
    )

    coordinator = NiftyOptionsV2AutoCycle()
    result = coordinator.process(
        expiries=EXPIRIES,
        observed_date=date(2026, 10, 29),
        observation=observation,
    )

    assert result is not None
    assert result.action is PaperAction.ENTER_NEXT_SERIES
    assert result.strike == 23500
    assert result.next_expiry == date(2026, 11, 26)

    active_trade = coordinator.auto_paper.session.trader.active_trade
    assert active_trade is not None
    assert active_trade.contract.expiry == date(2026, 11, 26)
    assert active_trade.contract.strike == 23500
    assert active_trade.entry_ltp == 1500
