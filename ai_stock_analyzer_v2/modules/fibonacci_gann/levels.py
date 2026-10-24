"""Pure price-level calculations for Fibonacci and Gann analysis.

The functions in this module are educational calculation helpers, not trade signals.
They intentionally do not retrieve market data, detect pivots, or place orders.
"""

from decimal import Decimal

type Price = Decimal | int | str

FIBONACCI_RETRACEMENT_RATIOS = (
    Decimal("0.236"),
    Decimal("0.382"),
    Decimal("0.500"),
    Decimal("0.618"),
    Decimal("0.786"),
)
FIBONACCI_EXTENSION_RATIOS = (
    Decimal("1.000"),
    Decimal("1.272"),
    Decimal("1.618"),
    Decimal("2.000"),
    Decimal("2.618"),
)


def _decimal(value: Price, name: str) -> Decimal:
    """Convert a supported numeric input to Decimal and reject invalid prices."""
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (ArithmeticError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite positive price") from exc
    if not result.is_finite() or result <= 0:
        raise ValueError(f"{name} must be a finite positive price")
    return result


def fibonacci_retracements(
    swing_low: Price,
    swing_high: Price,
) -> dict[str, Decimal]:
    """Return retracement prices for an upward swing from low to high.

    The returned levels are H - ratio * (H - L). The 50% level is a common
    market convention, not a Fibonacci sequence ratio. Inputs must satisfy H > L.
    """
    low = _decimal(swing_low, "swing_low")
    high = _decimal(swing_high, "swing_high")
    if high <= low:
        raise ValueError("swing_high must be greater than swing_low")
    swing_range = high - low
    return {
        f"{ratio * 100:.1f}%": high - ratio * swing_range for ratio in FIBONACCI_RETRACEMENT_RATIOS
    }


def fibonacci_extensions(
    swing_low: Price,
    swing_high: Price,
) -> dict[str, Decimal]:
    """Return upside targets H + ratio * (H - L), using extension beyond the high."""
    low = _decimal(swing_low, "swing_low")
    high = _decimal(swing_high, "swing_high")
    if high <= low:
        raise ValueError("swing_high must be greater than swing_low")
    swing_range = high - low
    return {f"{ratio:.3f}x": high + ratio * swing_range for ratio in FIBONACCI_EXTENSION_RATIOS}


def gann_eighths(swing_low: Price, swing_high: Price) -> dict[str, Decimal]:
    """Divide a price range into eight equal parts, including both endpoints."""
    low = _decimal(swing_low, "swing_low")
    high = _decimal(swing_high, "swing_high")
    if high <= low:
        raise ValueError("swing_high must be greater than swing_low")
    step = (high - low) / Decimal("8")
    return {f"{index}/8": low + step * index for index in range(9)}
