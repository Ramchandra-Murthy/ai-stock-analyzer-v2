"""Live-observation session helpers for NIFTY Options V2 paper trading."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from engine.nifty_options_v2_paper import NiftyOptionsV2PaperTrader, PaperTrade
from strategy.nifty_options_v2 import NiftyCallContract


@dataclass(frozen=True)
class LivePaperObservation:
    """One user-supplied current-market observation."""

    observed_date: date
    spot: float
    ltp: float


class NiftyOptionsV2LivePaperSession:
    """Manage a simulation-only paper session from current observations."""

    def __init__(self) -> None:
        self.trader = NiftyOptionsV2PaperTrader()
        self.contract: NiftyCallContract | None = None

    def start(
        self,
        *,
        expiry: date,
        strike: float,
        observation: LivePaperObservation,
    ) -> PaperTrade:
        """Start a paper position from a supplied live observation."""
        contract = NiftyCallContract(expiry=expiry, strike=strike)
        self.contract = contract
        return self.trader.enter(
            contract=contract,
            observed_date=observation.observed_date,
            spot=observation.spot,
            ltp=observation.ltp,
        )

    def update(self, observation: LivePaperObservation) -> PaperTrade | None:
        """Return the active paper trade; no order is sent to a broker."""
        del observation
        return self.trader.active_trade

    def close(self, observation: LivePaperObservation) -> PaperTrade:
        """Close the active paper trade using the supplied observation."""
        return self.trader.mark_exit(
            observed_date=observation.observed_date,
            ltp=observation.ltp,
        )
