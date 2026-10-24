"""OHLC validation and freshness checks for the isolated Fibonacci/Gann lab."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal


@dataclass(frozen=True)
class OHLCBar:
    """One timestamped OHLC candle with Decimal-compatible price values."""

    timestamp: datetime
    open: Decimal | int | str
    high: Decimal | int | str
    low: Decimal | int | str
    close: Decimal | int | str


@dataclass(frozen=True)
class DataQuality:
    """Validation outcome and diagnostic reasons."""

    valid: bool
    reasons: tuple[str, ...]
    latest_timestamp: datetime | None = None
    age: timedelta | None = None


def _price(value: Decimal | int | str, field: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (ArithmeticError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite positive price") from exc
    if not result.is_finite() or result <= 0:
        raise ValueError(f"{field} must be a finite positive price")
    return result


def validate_ohlc_bars(
    bars: Iterable[OHLCBar],
    *,
    now: datetime | None = None,
    max_age: timedelta = timedelta(minutes=15),
) -> DataQuality:
    """Validate candle geometry, timestamp order, and latest-bar freshness."""
    items = list(bars)
    if not items:
        return DataQuality(False, ("no OHLC bars supplied",))

    current = now or datetime.now(UTC)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if max_age < timedelta(0):
        raise ValueError("max_age must not be negative")

    reasons: list[str] = []
    previous: datetime | None = None
    for index, bar in enumerate(items):
        timestamp_valid = bar.timestamp.tzinfo is not None and bar.timestamp.utcoffset() is not None
        if not timestamp_valid:
            reasons.append(f"bar {index} timestamp is not timezone-aware")
        elif previous is not None and bar.timestamp <= previous:
            reasons.append(f"bar {index} timestamp is not strictly increasing")
        if timestamp_valid:
            previous = bar.timestamp

        try:
            opening = _price(bar.open, f"bar {index} open")
            high = _price(bar.high, f"bar {index} high")
            low = _price(bar.low, f"bar {index} low")
            close = _price(bar.close, f"bar {index} close")
            if high < max(opening, close, low) or low > min(opening, close, high):
                reasons.append(f"bar {index} has inconsistent OHLC values")
        except ValueError as exc:
            reasons.append(str(exc))

    latest = items[-1].timestamp
    age: timedelta | None = None
    if latest.tzinfo is None or latest.utcoffset() is None:
        reasons.append("latest timestamp is not timezone-aware")
    else:
        age = current - latest
        if age < timedelta(0):
            reasons.append("latest bar timestamp is in the future")
        elif age > max_age:
            reasons.append(f"latest bar is stale (age exceeds {max_age})")

    return DataQuality(not reasons, tuple(dict.fromkeys(reasons)), latest, age)
