from __future__ import annotations

"""
==========================================================
NET ASSET VALUE (NAV) MODEL
Module  : nav_model
Version : V1.0
==========================================================

Institutional NAV valuation engine.

Pipeline
--------
Validate
    ↓
Compute Asset Values
    ↓
Compute Liabilities
    ↓
Apply Minority Interest
    ↓
Apply HoldCo Discount
    ↓
Sensitivity Analysis
    ↓
Return NAVResult
"""

from services.valuation.nav.adjustments import (
    apply_holdco_discount,
    apply_minority_interest,
    total_adjusted_asset_value,
    total_fair_value_adjustment,
)
from services.valuation.nav.nav_input import NAVInput
from services.valuation.nav.nav_result import NAVResult
from services.valuation.nav.sensitivity import (
    build_nav_sensitivity_matrix,
)
from services.valuation.nav.validation import validate_input


class NAVModel:
    """
    Institutional Net Asset Value valuation engine.
    """

    def __init__(self, data: NAVInput):
        self.data = data

    def run_model(self) -> NAVResult:

        # ------------------------------------------
        # Validation
        # ------------------------------------------

        validate_input(self.data)

        # ------------------------------------------
        # Assets
        # ------------------------------------------

        gross_asset_value = total_adjusted_asset_value(self.data.assets)

        total_book_value = sum(
            asset.book_value * (asset.ownership_pct / 100.0)
            for asset in self.data.assets
            if asset.include_in_nav
        )

        fair_value_adjustment = total_fair_value_adjustment(self.data.assets)

        # ------------------------------------------
        # Liabilities
        # ------------------------------------------

        total_liabilities = sum(
            liability.amount for liability in self.data.liabilities if liability.include_in_nav
        )

        # ------------------------------------------
        # NAV Bridge
        # ------------------------------------------

        nav = gross_asset_value - total_liabilities

        adjusted_nav = apply_minority_interest(
            nav,
            self.data.minority_interest,
        )

        equity_value = apply_holdco_discount(
            adjusted_nav,
            self.data.holding_company_discount_pct,
        )

        share_price = equity_value / self.data.shares_outstanding

        # ------------------------------------------
        # Sensitivity
        # ------------------------------------------

        sensitivity = build_nav_sensitivity_matrix(
            gross_asset_value=gross_asset_value,
            total_liabilities=total_liabilities,
            minority_interest=self.data.minority_interest,
            shares_outstanding=self.data.shares_outstanding,
            base_holdco_discount=self.data.holding_company_discount_pct,
        )

        # ------------------------------------------
        # Assemble Result
        # ------------------------------------------

        return NAVResult(
            company_name=self.data.company_name,
            currency=self.data.currency,
            gross_asset_value=gross_asset_value,
            total_book_value=total_book_value,
            total_fair_value_adjustment=fair_value_adjustment,
            total_liabilities=total_liabilities,
            minority_interest=self.data.minority_interest,
            net_asset_value=nav,
            adjusted_nav=adjusted_nav,
            holding_company_discount_pct=self.data.holding_company_discount_pct,
            equity_value=equity_value,
            shares_outstanding=self.data.shares_outstanding,
            implied_share_price=share_price,
            asset_count=len(self.data.assets),
            liability_count=len(self.data.liabilities),
            included_asset_count=sum(1 for asset in self.data.assets if asset.include_in_nav),
            included_liability_count=sum(
                1 for liability in self.data.liabilities if liability.include_in_nav
            ),
            validation_passed=True,
            warnings=[],
            diagnostics={
                "sensitivity": sensitivity,
            },
        )
