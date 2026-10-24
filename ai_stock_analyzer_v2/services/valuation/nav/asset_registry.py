from __future__ import annotations

"""
==========================================================
NAV ASSET REGISTRY
Module  : asset_registry
Version : V1.0
==========================================================

Central registry of supported asset categories used by the
NAV valuation engine.

This registry standardizes asset classification across:

    • NAV Model
    • Research Reports
    • Portfolio Analytics
    • SOTP Engine
"""

from enum import StrEnum

# ==========================================================
# Asset Categories
# ==========================================================


class AssetCategory(StrEnum):

    # Financial Assets
    CASH = "CASH"
    CASH_EQUIVALENTS = "CASH_EQUIVALENTS"

    LISTED_EQUITY = "LISTED_EQUITY"
    UNLISTED_EQUITY = "UNLISTED_EQUITY"

    BONDS = "BONDS"
    MUTUAL_FUNDS = "MUTUAL_FUNDS"

    # Operating Assets
    PROPERTY = "PROPERTY"
    LAND = "LAND"

    PLANT_AND_MACHINERY = "PLANT_AND_MACHINERY"

    INFRASTRUCTURE = "INFRASTRUCTURE"

    INVENTORY = "INVENTORY"

    RECEIVABLES = "RECEIVABLES"

    # Intangible Assets
    GOODWILL = "GOODWILL"

    INTELLECTUAL_PROPERTY = "INTELLECTUAL_PROPERTY"

    LICENSES = "LICENSES"

    PATENTS = "PATENTS"

    TRADEMARKS = "TRADEMARKS"

    SOFTWARE = "SOFTWARE"

    # Investments
    STRATEGIC_INVESTMENT = "STRATEGIC_INVESTMENT"

    JOINT_VENTURE = "JOINT_VENTURE"

    ASSOCIATE = "ASSOCIATE"

    SUBSIDIARY = "SUBSIDIARY"

    # Other
    OTHER = "OTHER"


# ==========================================================
# Convenience Collections
# ==========================================================

FINANCIAL_ASSETS = {
    AssetCategory.CASH,
    AssetCategory.CASH_EQUIVALENTS,
    AssetCategory.LISTED_EQUITY,
    AssetCategory.UNLISTED_EQUITY,
    AssetCategory.BONDS,
    AssetCategory.MUTUAL_FUNDS,
}

OPERATING_ASSETS = {
    AssetCategory.PROPERTY,
    AssetCategory.LAND,
    AssetCategory.PLANT_AND_MACHINERY,
    AssetCategory.INFRASTRUCTURE,
    AssetCategory.INVENTORY,
    AssetCategory.RECEIVABLES,
}

INTANGIBLE_ASSETS = {
    AssetCategory.GOODWILL,
    AssetCategory.INTELLECTUAL_PROPERTY,
    AssetCategory.LICENSES,
    AssetCategory.PATENTS,
    AssetCategory.TRADEMARKS,
    AssetCategory.SOFTWARE,
}

INVESTMENT_ASSETS = {
    AssetCategory.STRATEGIC_INVESTMENT,
    AssetCategory.JOINT_VENTURE,
    AssetCategory.ASSOCIATE,
    AssetCategory.SUBSIDIARY,
}
