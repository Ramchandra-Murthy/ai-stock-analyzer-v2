from __future__ import annotations

"""
==========================================================
COMPARABLE COMPANY VALIDATION ENGINE
Module  : validation
Version : V1.0
==========================================================

Validates ComparableInput before valuation.

Checks include:
    • Target company financials
    • Peer company integrity
    • Duplicate peers
    • Positive financial metrics
"""

from services.valuation.comparable.comparable_input import (
    ComparableInput,
    PeerCompany,
)

# ==========================================================
# Peer Validation
# ==========================================================


def _validate_peer(peer: PeerCompany) -> None:

    if not peer.name.strip():
        raise ValueError("Peer company name cannot be empty.")

    if peer.enterprise_value <= 0:
        raise ValueError(f"{peer.name}: enterprise value must be positive.")

    if peer.market_cap <= 0:
        raise ValueError(f"{peer.name}: market capitalization must be positive.")

    if peer.revenue <= 0:
        raise ValueError(f"{peer.name}: revenue must be positive.")

    if peer.ebitda <= 0:
        raise ValueError(f"{peer.name}: EBITDA must be positive.")

    if peer.shares_outstanding <= 0:
        raise ValueError(f"{peer.name}: shares outstanding must be positive.")


# ==========================================================
# Main Validation
# ==========================================================


def validate_input(data: ComparableInput) -> None:

    target = data.target

    if not target.company_name.strip():
        raise ValueError("Target company name is required.")

    if target.revenue <= 0:
        raise ValueError("Target revenue must be positive.")

    if target.ebitda <= 0:
        raise ValueError("Target EBITDA must be positive.")

    if target.shares_outstanding <= 0:
        raise ValueError("Target shares outstanding must be positive.")

    if len(data.peers) == 0:
        raise ValueError("At least one comparable peer is required.")

    peer_names = set()

    for peer in data.peers:

        _validate_peer(peer)

        if peer.name in peer_names:
            raise ValueError(f"Duplicate peer company detected: {peer.name}")

        peer_names.add(peer.name)
