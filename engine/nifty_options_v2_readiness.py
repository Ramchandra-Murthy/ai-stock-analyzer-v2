"""Final safety gate for NIFTY Options V2 automatic paper processing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class V2Readiness:
    """Explain whether all required safety gates permit automatic paper processing."""

    provider_ready: bool
    market_session_ready: bool
    market_data_fresh: bool

    @property
    def ready(self) -> bool:
        """Return whether every required safety gate is satisfied."""
        return self.provider_ready and self.market_session_ready and self.market_data_fresh


def automatic_cycle_ready(
    *,
    provider_ready: bool,
    market_session_ready: bool,
    market_data_fresh: bool,
) -> V2Readiness:
    """Build the final readiness result without changing strategy or broker behavior."""
    return V2Readiness(
        provider_ready=provider_ready,
        market_session_ready=market_session_ready,
        market_data_fresh=market_data_fresh,
    )
