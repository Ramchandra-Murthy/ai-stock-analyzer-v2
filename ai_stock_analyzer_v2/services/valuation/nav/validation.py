from __future__ import annotations

"""
==========================================================
NAV VALIDATION ENGINE
Module  : validation
Version : V1.0
==========================================================

Validates NAVInput before valuation.

Checks include:
    • Company metadata
    • Asset integrity
    • Liability integrity
    • Ownership percentages
    • Holding company discount
    • Share count
"""

from services.valuation.nav.nav_input import (
    NAVAsset,
    NAVInput,
    NAVLiability,
)

# ==========================================================
# Asset Validation
# ==========================================================


def _validate_asset(asset: NAVAsset) -> None:

    if not asset.name.strip():
        raise ValueError("Asset name cannot be empty.")

    if asset.book_value < 0:
        raise ValueError(f"{asset.name}: book_value cannot be negative.")

    if asset.fair_value < 0:
        raise ValueError(f"{asset.name}: fair_value cannot be negative.")

    if not (0 <= asset.ownership_pct <= 100):
        raise ValueError(f"{asset.name}: ownership_pct must be between 0 and 100.")


# ==========================================================
# Liability Validation
# ==========================================================


def _validate_liability(liability: NAVLiability) -> None:

    if not liability.name.strip():
        raise ValueError("Liability name cannot be empty.")

    if liability.amount < 0:
        raise ValueError(f"{liability.name}: liability amount cannot be negative.")


# ==========================================================
# Main Validation
# ==========================================================


def validate_input(data: NAVInput) -> None:

    if not data.company_name.strip():
        raise ValueError("Company name is required.")

    if data.shares_outstanding <= 0:
        raise ValueError("Shares outstanding must be greater than zero.")

    if not (0 <= data.holding_company_discount_pct <= 1):
        raise ValueError("Holding company discount must be between 0 and 1.")

    if data.minority_interest < 0:
        raise ValueError("Minority interest cannot be negative.")

    asset_names = set()

    for asset in data.assets:

        _validate_asset(asset)

        if asset.name in asset_names:
            raise ValueError(f"Duplicate asset detected: {asset.name}")

        asset_names.add(asset.name)

    liability_names = set()

    for liability in data.liabilities:

        _validate_liability(liability)

        if liability.name in liability_names:
            raise ValueError(f"Duplicate liability detected: {liability.name}")

        liability_names.add(liability.name)
