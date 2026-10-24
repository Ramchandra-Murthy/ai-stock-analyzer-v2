"""Tests for the NIFTY Options V2 monthly cycle status."""

# ruff: noqa: I001

from datetime import date

from engine.nifty_options_v2_auto import PaperAction
from engine.nifty_options_v2_cycle_status import cycle_status

EXPIRIES = ("2026-10-29", "2026-11-26")


def test_cycle_status_reports_hold_between_expiries() -> None:
    status = cycle_status(
        expiries=EXPIRIES,
        observed_date=date(2026, 10, 20),
        active_contract_expiry=date(2026, 10, 29),
    )

    assert status is not None
    assert status.current_expiry == date(2026, 10, 29)
    assert status.next_expiry == date(2026, 11, 26)
    assert status.action is PaperAction.HOLD


def test_cycle_status_reports_next_series_entry_on_current_expiry() -> None:
    status = cycle_status(
        expiries=EXPIRIES,
        observed_date=date(2026, 10, 29),
        active_contract_expiry=None,
    )

    assert status is not None
    assert status.action is PaperAction.ENTER_NEXT_SERIES


def test_cycle_status_requires_two_monthly_expiries() -> None:
    assert (
        cycle_status(
            expiries=("2026-10-29",),
            observed_date=date(2026, 10, 20),
            active_contract_expiry=None,
        )
        is None
    )
