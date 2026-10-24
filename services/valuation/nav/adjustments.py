from __future__ import annotations

"""
==========================================================
NAV ADJUSTMENT ENGINE
Module  : adjustments
Version : V1.0
==========================================================

Institutional NAV adjustment routines.

Responsible for applying:

• Fair value adjustments
• Ownership adjustments
• Minority interest deductions
• Holding company discounts

The module is intentionally independent of NAVModel so
individual adjustments can be unit tested.
"""

from services.valuation.nav.nav_input import (
    NAVAsset,
)

# ==========================================================
# Fair Value
# ==========================================================


def adjusted_asset_value(asset: NAVAsset) -> float:
    """
    Computes the adjusted economic value of an asset after
    ownership adjustment.

    Formula:
        Fair Value × Ownership %
    """

    if not asset.include_in_nav:
        return 0.0

    return asset.fair_value * (asset.ownership_pct / 100.0)


def fair_value_adjustment(asset: NAVAsset) -> float:
    """
    Calculates uplift (or impairment) versus book value.
    """

    if not asset.include_in_nav:
        return 0.0

    adjusted_book = asset.book_value * (asset.ownership_pct / 100.0)

    adjusted_fair = adjusted_asset_value(asset)

    return adjusted_fair - adjusted_book


# ==========================================================
# Minority Interest
# ==========================================================


def apply_minority_interest(
    nav: float,
    minority_interest: float,
) -> float:
    """
    Deduct minority interest from NAV.
    """

    return nav - minority_interest


# ==========================================================
# Holding Company Discount
# ==========================================================


def apply_holdco_discount(
    equity_value: float,
    discount_pct: float,
) -> float:
    """
    Applies holding company discount.

    discount_pct:
        0.15 means 15%
    """

    return equity_value * (1.0 - discount_pct)


# ==========================================================
# Aggregate Fair Value
# ==========================================================


def total_adjusted_asset_value(
    assets: list[NAVAsset],
) -> float:
    """
    Total economic value of included assets.
    """

    return sum(adjusted_asset_value(asset) for asset in assets)


def total_fair_value_adjustment(
    assets: list[NAVAsset],
) -> float:
    """
    Aggregate uplift versus book values.
    """

    return sum(fair_value_adjustment(asset) for asset in assets)
