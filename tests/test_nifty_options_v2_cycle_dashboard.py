from datetime import date

from engine.nifty_options_v2_auto import PaperAction
from engine.nifty_options_v2_cycle_status import cycle_status


def test_dashboard_cycle_status_exposes_book_v2_action() -> None:
    status = cycle_status(
        expiries=("2026-10-29", "2026-11-26"),
        observed_date=date(2026, 10, 20),
        active_contract_expiry=date(2026, 10, 29),
    )

    assert status is not None
    assert status.action is PaperAction.HOLD
    assert status.current_expiry == date(2026, 10, 29)
    assert status.next_expiry == date(2026, 11, 26)
