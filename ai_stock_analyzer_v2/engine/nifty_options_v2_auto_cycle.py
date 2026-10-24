"""Automatic monthly cycle coordinator for NIFTY Options V2 paper trading."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from engine.nifty_options_v2_auto import NiftyOptionsV2AutoPaper, PaperAction, V2TimingDecision
from engine.nifty_options_v2_cycle_status import cycle_status
from engine.nifty_options_v2_market_data import NiftyV2MarketObservation


@dataclass(frozen=True)
class AutoCycleResult:
    """Cycle status and execution decision for one supplied observation."""

    action: PaperAction
    reason: str
    current_expiry: date
    next_expiry: date
    observed_date: date
    strike: float
    spot: float
    ltp: float


class NiftyOptionsV2AutoCycle:
    """Coordinate monthly timing decisions with the paper-only state machine."""

    def __init__(self, auto_paper: NiftyOptionsV2AutoPaper | None = None) -> None:
        self.auto_paper = auto_paper or NiftyOptionsV2AutoPaper()

    def process(
        self,
        *,
        expiries: tuple[str, ...],
        observed_date: date,
        observation: NiftyV2MarketObservation,
    ) -> AutoCycleResult | None:
        """Process one supplied observation without submitting broker orders."""
        active_trade = self.auto_paper.session.trader.active_trade
        active_expiry = active_trade.contract.expiry if active_trade is not None else None

        if active_expiry is not None and observed_date >= active_expiry:
            decision = self.auto_paper.process(
                observation=observation,
                current_series_expiry=active_expiry,
            )
            if decision.action is not PaperAction.EXIT_EXPIRY:
                return None
            return AutoCycleResult(
                action=decision.action,
                reason=decision.reason,
                current_expiry=active_expiry,
                next_expiry=active_expiry,
                observed_date=observation.observation.observed_date,
                strike=observation.contract.strike,
                spot=observation.observation.spot,
                ltp=observation.observation.ltp,
            )

        status = cycle_status(
            expiries=expiries,
            observed_date=observed_date,
            active_contract_expiry=active_expiry,
        )
        if status is None:
            return None

        decision: V2TimingDecision = self.auto_paper.process(
            observation=observation,
            current_series_expiry=status.current_expiry,
        )
        return AutoCycleResult(
            action=decision.action,
            reason=decision.reason,
            current_expiry=status.current_expiry,
            next_expiry=status.next_expiry,
            observed_date=observation.observation.observed_date,
            strike=observation.contract.strike,
            spot=observation.observation.spot,
            ltp=observation.observation.ltp,
        )
