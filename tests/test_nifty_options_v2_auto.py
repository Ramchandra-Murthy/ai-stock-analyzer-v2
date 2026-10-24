from datetime import date

import pytest

from engine.nifty_options_v2_auto import PaperAction, decide_timing


def test_expiry_day_without_active_trade_enters_next_series() -> None:
    decision = decide_timing(
        observed_date=date(2026, 10, 29),
        current_series_expiry=date(2026, 10, 29),
        active_contract_expiry=None,
    )

    assert decision.action is PaperAction.ENTER_NEXT_SERIES


def test_active_trade_is_held_before_its_expiry() -> None:
    decision = decide_timing(
        observed_date=date(2026, 10, 20),
        current_series_expiry=date(2026, 10, 29),
        active_contract_expiry=date(2026, 10, 29),
    )

    assert decision.action is PaperAction.HOLD


def test_active_trade_exits_on_expiry() -> None:
    decision = decide_timing(
        observed_date=date(2026, 10, 29),
        current_series_expiry=date(2026, 10, 29),
        active_contract_expiry=date(2026, 10, 29),
    )

    assert decision.action is PaperAction.EXIT_EXPIRY


def test_timing_rejects_observation_after_current_expiry() -> None:
    with pytest.raises(ValueError, match="current series expiry"):
        decide_timing(
            observed_date=date(2026, 10, 30),
            current_series_expiry=date(2026, 10, 29),
            active_contract_expiry=None,
        )
