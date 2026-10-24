from __future__ import annotations

from typing import Any

from services.valuation.base_engine import BaseValuationEngine
from services.valuation.models import ValuationMethod, ValuationResult, ValuationStatus


class NAVValuationEngine(BaseValuationEngine):
    """Net Asset Value (NAV) Stub Engine for Real Estate & Holding Companies."""

    @property
    def valuation_method(self) -> str:
        return ValuationMethod.NAV.value

    def value(self, entity: Any) -> ValuationResult:
        entity_name = getattr(entity, "segment_name", str(entity))
        return ValuationResult(
            entity_name=entity_name,
            valuation_method=ValuationMethod.NAV,
            valuation_status=ValuationStatus.PENDING,
            enterprise_value=0.0,
            equity_value=0.0,
            diagnostics={"error": "NAV Valuation Engine scheduled for Phase 3 implementation."},
        )


class MarketValuationEngine(BaseValuationEngine):
    """Quoted Market Value Stub Engine for Listed Subsidiaries."""

    @property
    def valuation_method(self) -> str:
        return ValuationMethod.MARKET.value

    def value(self, entity: Any) -> ValuationResult:
        entity_name = getattr(entity, "segment_name", str(entity))
        return ValuationResult(
            entity_name=entity_name,
            valuation_method=ValuationMethod.MARKET,
            valuation_status=ValuationStatus.PENDING,
            enterprise_value=0.0,
            equity_value=0.0,
            diagnostics={"error": "Market Valuation Engine scheduled for Phase 3 implementation."},
        )


class BookValueEngine(BaseValuationEngine):
    """Book Value Stub Engine for Financial & Distressed Segments."""

    @property
    def valuation_method(self) -> str:
        return ValuationMethod.BOOK_VALUE.value

    def value(self, entity: Any) -> ValuationResult:
        entity_name = getattr(entity, "segment_name", str(entity))
        return ValuationResult(
            entity_name=entity_name,
            valuation_method=ValuationMethod.BOOK_VALUE,
            valuation_status=ValuationStatus.PENDING,
            enterprise_value=0.0,
            equity_value=0.0,
            diagnostics={"error": "Book Value Engine scheduled for Phase 3 implementation."},
        )
