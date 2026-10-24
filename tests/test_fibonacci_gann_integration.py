"""Integration tests for validated bars, confirmed swings, and confluence zones."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from modules.fibonacci_gann.confluence import find_confluence_zones
from modules.fibonacci_gann.market_data import OHLCBar, validate_ohlc_bars
from modules.fibonacci_gann.swings import detect_confirmed_swings


def test_validated_bars_flow_into_confirmed_swings_and_confluence() -> None:
    now = datetime.now(UTC)
    highs = [12, 14, 20, 15, 13, 16, 17]
    lows = [9, 8, 10, 11, 7, 12, 13]
    bars = [
        OHLCBar(
            timestamp=now - timedelta(minutes=len(highs) - index - 1),
            open=low,
            high=high,
            low=low,
            close=low,
        )
        for index, (high, low) in enumerate(zip(highs, lows, strict=True))
    ]

    quality = validate_ohlc_bars(bars, now=now, max_age=timedelta(minutes=15))
    assert quality.valid, quality.reasons

    swings = detect_confirmed_swings(bars, left_bars=1, right_bars=1)
    swing_low = next(point for point in swings if point.index == 1 and point.kind == "low")
    swing_high = next(point for point in swings if point.index == 2 and point.kind == "high")

    # The high at index 2 is only usable after the following bar confirms it.
    assert swing_low.price == Decimal("8")
    assert swing_high.price == Decimal("20")
    assert swing_high.index < len(bars) - 1

    zones = find_confluence_zones(swing_low.price, swing_high.price, tolerance="0.5")
    assert zones
    assert zones == sorted(zones, key=lambda zone: zone.low)
    assert all(zone.distance <= Decimal("0.5") for zone in zones)
    assert all(len(zone.levels) >= 2 for zone in zones)
