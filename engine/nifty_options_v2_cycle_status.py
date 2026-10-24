"""Monthly cycle status for the NIFTY Options V2 paper workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from engine.nifty_options_v2_auto import PaperAction, decide_timing
from engine.nifty_options_v2_cycle import current_and_next_monthly_expiry


@dataclass(frozen=True)
class V2CycleStatus:
    """Current and next monthly series with the Book V2 action."""

    current_expiry: date
    next_expiry: date
    action: PaperAction
    reason: str


def cycle_status(
    *,
    expiries: tuple[str, ...],
    observed_date: date,
    active_contract_expiry: date | None,
) -> V2CycleStatus | None:
    """Return the Book V2 cycle status when two monthly expiries are available."""
    pair = current_and_next_monthly_expiry(expiries)
    if pair is None:
        return None

    current_expiry, next_expiry = pair
    decision = decide_timing(
        observed_date=observed_date,
        current_series_expiry=current_expiry,
        active_contract_expiry=active_contract_expiry,
    )
    return V2CycleStatus(
        current_expiry=current_expiry,
        next_expiry=next_expiry,
        action=decision.action,
        reason=decision.reason,
    )
