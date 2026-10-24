"""Book V2 monthly timing rules for simulation-only paper trading."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from engine.nifty_options_v2_live import LivePaperObservation, NiftyOptionsV2LivePaperSession
from engine.nifty_options_v2_market_data import NiftyV2MarketObservation


class PaperAction(StrEnum):
    """Action requested by the Book V2 monthly state machine."""

    HOLD = "hold"
    ENTER_NEXT_SERIES = "enter_next_series"
    EXIT_EXPIRY = "exit_expiry"


@dataclass(frozen=True)
class V2TimingDecision:
    """A deterministic timing decision for one market observation."""

    action: PaperAction
    reason: str


def decide_timing(
    *,
    observed_date: date,
    current_series_expiry: date,
    active_contract_expiry: date | None,
) -> V2TimingDecision:
    """Apply the Book V2 expiry-day entry/exit timing rules."""
    if observed_date > current_series_expiry:
        raise ValueError("observed_date cannot follow current series expiry")

    if active_contract_expiry is not None and observed_date >= active_contract_expiry:
        return V2TimingDecision(
            action=PaperAction.EXIT_EXPIRY,
            reason="held series has reached expiry",
        )

    if active_contract_expiry is None and observed_date == current_series_expiry:
        return V2TimingDecision(
            action=PaperAction.ENTER_NEXT_SERIES,
            reason="current series expiry: enter next series",
        )

    return V2TimingDecision(action=PaperAction.HOLD, reason="hold without adjustment")


class NiftyOptionsV2AutoPaper:
    """Apply timing decisions to a simulation-only paper session."""

    def __init__(self, session: NiftyOptionsV2LivePaperSession | None = None) -> None:
        self.session = session or NiftyOptionsV2LivePaperSession()

    def process(
        self,
        *,
        observation: NiftyV2MarketObservation,
        current_series_expiry: date,
    ) -> V2TimingDecision:
        """Process one supplied observation without sending any broker order."""
        active_trade = self.session.trader.active_trade
        active_expiry = active_trade.contract.expiry if active_trade is not None else None
        decision = decide_timing(
            observed_date=observation.observation.observed_date,
            current_series_expiry=current_series_expiry,
            active_contract_expiry=active_expiry,
        )

        if decision.action is PaperAction.EXIT_EXPIRY:
            self.session.close(
                LivePaperObservation(
                    observed_date=observation.observation.observed_date,
                    spot=observation.observation.spot,
                    ltp=observation.observation.ltp,
                )
            )
        elif decision.action is PaperAction.ENTER_NEXT_SERIES:
            self.session.start(
                expiry=observation.contract.expiry,
                strike=observation.contract.strike,
                observation=observation.observation,
            )

        return decision
