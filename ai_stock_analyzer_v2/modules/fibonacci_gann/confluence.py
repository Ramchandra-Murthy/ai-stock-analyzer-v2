"""Deterministic Fibonacci/Gann level confluence analysis.

Confluence zones summarize nearby calculated levels. They are not trade signals.
This module does not retrieve data, detect swings, size positions, or place orders.
"""

from dataclasses import dataclass
from decimal import Decimal

from modules.fibonacci_gann.levels import (
    Price,
    fibonacci_extensions,
    fibonacci_retracements,
    gann_eighths,
)


@dataclass(frozen=True)
class PriceLevel:
    """One named calculated level and the family it belongs to."""

    family: str
    label: str
    price: Decimal


@dataclass(frozen=True)
class ConfluenceZone:
    """A bounded group of nearby levels, with their arithmetic midpoint."""

    low: Decimal
    high: Decimal
    center: Decimal
    levels: tuple[PriceLevel, ...]

    @property
    def distance(self) -> Decimal:
        """Return the width of this zone in price units."""
        return self.high - self.low


def calculate_levels(swing_low: Price, swing_high: Price) -> tuple[PriceLevel, ...]:
    """Calculate Fibonacci retracements/extensions and Gann eighths for one swing."""
    retracements = fibonacci_retracements(swing_low, swing_high)
    extensions = fibonacci_extensions(swing_low, swing_high)
    eighths = gann_eighths(swing_low, swing_high)
    levels = [
        PriceLevel("fibonacci_retracement", label, price) for label, price in retracements.items()
    ]
    levels.extend(
        PriceLevel("fibonacci_extension", label, price) for label, price in extensions.items()
    )
    levels.extend(PriceLevel("gann_eighth", label, price) for label, price in eighths.items())
    return tuple(sorted(levels, key=lambda level: (level.price, level.family, level.label)))


def find_confluence_zones(
    swing_low: Price,
    swing_high: Price,
    *,
    tolerance: Price = "1",
) -> list[ConfluenceZone]:
    """Return groups of at least two levels whose total price span is within tolerance.

    Levels are sorted by price and grouped greedily without chaining beyond the
    configured maximum span. The zone center is the midpoint of its lowest and
    highest member. Single levels are omitted; exact overlaps are included even
    when tolerance is zero. Results are deterministic and sorted by price.
    """
    try:
        allowed_span = Decimal(str(tolerance))
    except (ArithmeticError, ValueError) as exc:
        raise ValueError("tolerance must be a finite non-negative price distance") from exc
    if not allowed_span.is_finite() or allowed_span < 0:
        raise ValueError("tolerance must be a finite non-negative price distance")

    levels = calculate_levels(swing_low, swing_high)
    groups: list[list[PriceLevel]] = []
    current: list[PriceLevel] = []
    group_low: Decimal | None = None

    for level in levels:
        if not current:
            current = [level]
            group_low = level.price
        elif group_low is not None and level.price - group_low <= allowed_span:
            current.append(level)
        else:
            if len(current) >= 2:
                groups.append(current)
            current = [level]
            group_low = level.price

    if len(current) >= 2:
        groups.append(current)

    zones = []
    for group in groups:
        low = group[0].price
        high = group[-1].price
        zones.append(
            ConfluenceZone(
                low=low,
                high=high,
                center=(low + high) / Decimal(2),
                levels=tuple(group),
            )
        )
    return zones
