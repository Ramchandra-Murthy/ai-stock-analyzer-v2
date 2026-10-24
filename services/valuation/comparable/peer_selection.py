from __future__ import annotations

"""
==========================================================
COMPARABLE COMPANY PEER SELECTION
Module  : peer_selection
Version : V1.0
==========================================================

Responsible for selecting and filtering comparable companies.

Current Version
---------------
• Manual peer validation
• Duplicate removal
• Basic filtering

Future Versions
---------------
• Industry classification
• Sector filtering
• Market-cap filtering
• Geographic filtering
• AI similarity scoring
"""


from services.valuation.comparable.comparable_input import PeerCompany

# ==========================================================
# Remove Duplicate Peers
# ==========================================================


def remove_duplicate_peers(
    peers: list[PeerCompany],
) -> list[PeerCompany]:

    unique = {}

    for peer in peers:

        key = peer.ticker.upper().strip()

        if key not in unique:
            unique[key] = peer

    return list(unique.values())


# ==========================================================
# Basic Financial Filter
# ==========================================================


def filter_valid_peers(
    peers: list[PeerCompany],
) -> list[PeerCompany]:

    valid = []

    for peer in peers:

        if (
            peer.enterprise_value > 0
            and peer.market_cap > 0
            and peer.revenue > 0
            and peer.ebitda > 0
            and peer.shares_outstanding > 0
        ):
            valid.append(peer)

    return valid


# ==========================================================
# Manual Peer Selection
# ==========================================================


def select_peers(
    peers: list[PeerCompany],
) -> list[PeerCompany]:
    """
    Current peer selection pipeline.

    Future versions will include AI-assisted
    and industry-based selection.
    """

    peers = remove_duplicate_peers(peers)

    peers = filter_valid_peers(peers)

    return peers
