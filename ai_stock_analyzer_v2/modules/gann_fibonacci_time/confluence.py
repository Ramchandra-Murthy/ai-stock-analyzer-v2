"""Deterministic confluence tagging for research events."""

from __future__ import annotations


def eligible_time_zone_indices(
    time_zone_indices: list[int] | tuple[int, ...],
    confirmed_at_index: int,
    total_bars: int,
) -> list[int]:
    """Return historical time zones observable at or after anchor confirmation.

    A pivot's historical location may precede the bar on which it becomes known.
    Confluence must not be evaluated before that confirmation bar has closed.
    """
    if isinstance(confirmed_at_index, bool) or not isinstance(confirmed_at_index, int):
        raise ValueError("confirmed_at_index must be an integer.")
    if isinstance(total_bars, bool) or not isinstance(total_bars, int) or total_bars < 0:
        raise ValueError("total_bars must be a non-negative integer.")
    if confirmed_at_index < 0:
        raise ValueError("confirmed_at_index must be non-negative.")
    return sorted(
        {
            index
            for index in time_zone_indices
            if isinstance(index, int)
            and not isinstance(index, bool)
            and confirmed_at_index <= index < total_bars
        }
    )


def find_confluence(
    time_zone_indices: list[int] | tuple[int, ...],
    price_projections: list[dict[str, int | float | str]],
    observed_prices: dict[int, float],
    tolerance_pct: float = 0.5,
) -> list[dict[str, int | float]]:
    """Tag a time-zone bar when its close is near a projected Gann level."""
    if not 0 <= tolerance_pct < 100:
        raise ValueError("tolerance_pct must be in [0, 100).")
    zones, matches = set(time_zone_indices), []
    for projection in price_projections:
        index = projection["target_index"]
        projected = float(projection["price"])
        if index not in zones or index not in observed_prices:
            continue
        observed = float(observed_prices[index])
        if observed <= 0 or projected <= 0:
            continue
        distance = abs(observed - projected) / projected * 100
        if distance <= tolerance_pct:
            matches.append(
                {
                    "bar_index": index,
                    "ratio": float(projection["ratio"]),
                    "projected_price": projected,
                    "observed_price": observed,
                    "distance_pct": distance,
                }
            )
    return sorted(
        matches,
        key=lambda item: (int(item["bar_index"]), float(item["distance_pct"])),
    )
