from __future__ import annotations

"""
==========================================================
NAV ENGINE ADAPTER
Module  : nav_engine
Version : V1.0
==========================================================

Adapter exposing the NAV package via the BaseValuationEngine interface.
"""

from typing import Any

from services.valuation.base_engine import BaseValuationEngine
from services.valuation.models import (
    ValuationMethod,
    ValuationResult,
    ValuationStatus,
)
from services.valuation.nav.nav_input import NAVAsset, NAVInput, NAVLiability
from services.valuation.nav.nav_model import NAVModel


class NAVEngine(BaseValuationEngine):
    """Adapter class wrapping NAVModel for the ValuationDispatcher framework."""

    @property
    def valuation_method(self) -> str:
        return ValuationMethod.NAV.value

    def value(self, entity: Any) -> ValuationResult:
        if isinstance(entity, NAVInput):
            nav_input = entity
        elif isinstance(entity, dict):
            nav_input = self._parse_dict_payload(entity)
        else:
            raise TypeError(f"NAVEngine received unsupported payload type: {type(entity)}")

        model = NAVModel(nav_input)
        nav_res = model.run_model()

        return ValuationResult(
            entity_name=nav_res.company_name,
            valuation_method=ValuationMethod.NAV,
            valuation_status=ValuationStatus.COMPLETE,
            enterprise_value=nav_res.gross_asset_fair_value,
            equity_value=nav_res.equity_nav,
            diagnostics={
                "gross_asset_book_value": nav_res.gross_asset_book_value,
                "gross_asset_fair_value": nav_res.gross_asset_fair_value,
                "total_liabilities": nav_res.total_liabilities,
                "raw_nav": nav_res.net_asset_value,
                "adjusted_nav": nav_res.adjusted_nav,
                "holdco_discount_amount": nav_res.holding_company_discount_amount,
                "implied_share_price": nav_res.implied_share_price,
                "category_breakdown": nav_res.category_breakdown,
            },
            raw_result=nav_res,
        )

    def _parse_dict_payload(self, data: dict[str, Any]) -> NAVInput:
        assets = [
            NAVAsset(
                name=a.get("name", "Unnamed Asset"),
                category=a.get("category", "Other"),
                book_value=float(a.get("book_value", 0.0)),
                fair_value=float(a.get("fair_value", a.get("book_value", 0.0))),
                ownership_pct=float(a.get("ownership_pct", 100.0)),
                include_in_nav=bool(a.get("include_in_nav", True)),
                notes=a.get("notes", ""),
            )
            for a in data.get("assets", [])
        ]

        liabilities = [
            NAVLiability(
                name=l.get("name", "Unnamed Liability"),
                category=l.get("category", "Debt"),
                amount=float(l.get("amount", 0.0)),
                include_in_nav=bool(l.get("include_in_nav", True)),
                notes=l.get("notes", ""),
            )
            for l in data.get("liabilities", [])
        ]

        return NAVInput(
            company_name=data.get("segment_name", data.get("company_name", "NAV Entity")),
            currency=data.get("currency", "INR"),
            assets=assets,
            liabilities=liabilities,
            minority_interest=float(data.get("minority_interest", 0.0)),
            holding_company_discount_pct=float(
                data.get("holding_company_discount_pct", data.get("holdco_discount_pct", 0.0))
            ),
            shares_outstanding=float(data.get("shares_outstanding", 1.0)),
        )
