"""Tests for deterministic Fibonacci/Gann confluence analysis."""

from decimal import Decimal

import pytest

from modules.fibonacci_gann.confluence import (
    PriceLevel,
    calculate_levels,
    find_confluence_zones,
)


def test_calculated_levels_include_all_three_families() -> None:
    levels = calculate_levels(800, 1000)
    families = {level.family for level in levels}

    assert families == {"fibonacci_retracement", "fibonacci_extension", "gann_eighth"}
    assert len(levels) == 19
    assert all(isinstance(level.price, Decimal) for level in levels)


def test_exact_fibonacci_gann_overlap_is_reported_with_zero_tolerance() -> None:
    zones = find_confluence_zones(800, 1000, tolerance=0)
    midpoint = next(zone for zone in zones if zone.center == Decimal("900"))

    assert midpoint.low == Decimal("900.000")
    assert midpoint.high == Decimal("900.000")
    assert {level.label for level in midpoint.levels} == {"50.0%", "4/8"}
    assert midpoint.distance == 0


def test_nearby_levels_form_bounded_zone() -> None:
    zones = find_confluence_zones(800, 1000, tolerance="2")

    assert zones
    assert all(zone.distance <= Decimal("2") for zone in zones)
    assert all(len(zone.levels) >= 2 for zone in zones)
    assert all(zone.low <= zone.center <= zone.high for zone in zones)


def test_levels_outside_tolerance_are_not_combined() -> None:
    zones = find_confluence_zones(800, 1000, tolerance="0.01")

    assert all(zone.distance <= Decimal("0.01") for zone in zones)
    assert not any(
        level.family == "fibonacci_retracement"
        and level.label == "38.2%"
        and any(item.family == "gann_eighth" and item.label == "5/8" for item in zone.levels)
        for zone in zones
        for level in zone.levels
    )


@pytest.mark.parametrize("tolerance", [-1, "-0.1", "NaN", "Infinity", True, None, "invalid"])
def test_invalid_tolerance_is_rejected(tolerance: object) -> None:
    with pytest.raises(ValueError):
        find_confluence_zones(800, 1000, tolerance=tolerance)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("low", "high"),
    [(0, 100), (100, 100), (200, 100), ("NaN", 100), (100, "Infinity")],
)
def test_invalid_swing_is_rejected(low: int | str, high: int | str) -> None:
    with pytest.raises(ValueError):
        find_confluence_zones(low, high)


def test_zone_order_and_contents_are_deterministic() -> None:
    first = find_confluence_zones(800, 1000, tolerance="5")
    second = find_confluence_zones(800, 1000, tolerance="5")

    assert first == second
    assert [zone.low for zone in first] == sorted(zone.low for zone in first)


def test_levels_exactly_at_tolerance_boundary_are_grouped() -> None:
    zones = find_confluence_zones(800, 1000, tolerance="1.4")

    boundary_zone = next(
        zone for zone in zones if {level.label for level in zone.levels} >= {"61.8%", "3/8"}
    )
    assert boundary_zone.low == Decimal("875.000")
    assert boundary_zone.high == Decimal("876.400")
    assert boundary_zone.distance == Decimal("1.400")


def test_confluence_groups_do_not_chain_beyond_total_tolerance(monkeypatch) -> None:
    levels = (
        PriceLevel("test", "A", Decimal("100")),
        PriceLevel("test", "B", Decimal("101")),
        PriceLevel("test", "C", Decimal("102.1")),
    )
    monkeypatch.setattr(
        "modules.fibonacci_gann.confluence.calculate_levels",
        lambda _low, _high: levels,
    )

    zones = find_confluence_zones(1, 2, tolerance="1")

    assert len(zones) == 1
    assert [level.label for level in zones[0].levels] == ["A", "B"]
    assert zones[0].low == Decimal("100")
    assert zones[0].high == Decimal("101")
    assert zones[0].distance == Decimal("1")
