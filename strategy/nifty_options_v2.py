"""Domain models for the NIFTY Options Book V2 data layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class NiftyCallContract:
    """Identify one NIFTY CALL option contract."""

    expiry: date
    strike: float

    def __post_init__(self) -> None:
        if self.strike <= 0:
            raise ValueError("strike must be positive")


@dataclass(frozen=True)
class NiftyCallObservation:
    """Observed market data for a NIFTY CALL contract."""

    contract: NiftyCallContract
    observed_date: date
    spot: float
    ltp: float

    def __post_init__(self) -> None:
        if self.spot <= 0:
            raise ValueError("spot must be positive")
        if self.ltp < 0:
            raise ValueError("ltp must be non-negative")

    @property
    def is_itm(self) -> bool:
        """Return whether the CALL strike is below the observed NIFTY spot."""
        return self.contract.strike < self.spot

    @property
    def is_deep_itm(self) -> bool:
        """Return the same ITM classification used by V2 without inventing a threshold."""
        return self.is_itm
