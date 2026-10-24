"""Provider readiness checks for NIFTY Options V2 paper trading."""

from __future__ import annotations

from services.options_analytics import OptionChainResult


def provider_data_ready(result: OptionChainResult) -> bool:
    """Return whether a provider result is safe for automatic paper processing."""
    return result.status == "AVAILABLE" and result.spot is not None and not result.chain.empty
