"""Strike selection rules for NIFTY Options Book V2."""

from __future__ import annotations


def select_deepest_itm_call(strikes: list[float], spot: float) -> float:
    """Select the lowest available CALL strike below the observed spot.

    The book requires an ITM CALL and prefers deep ITM to reduce time premium,
    but does not define a numeric deep-ITM threshold. This selector therefore
    uses the deepest available ITM strike without inventing a threshold.
    """
    if spot <= 0:
        raise ValueError("spot must be positive")
    if not strikes:
        raise ValueError("at least one strike is required")
    itm = [strike for strike in strikes if 0 < strike < spot]
    if not itm:
        raise ValueError("no ITM CALL strike is available below spot")
    return min(itm)
