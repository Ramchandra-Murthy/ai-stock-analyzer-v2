from __future__ import annotations

from typing import Any

from services.valuation.base_engine import BaseValuationEngine
from services.valuation.models import ValuationMethod, ValuationResult, ValuationStatus
from services.valuation.nav import NAVInput, NAVModel


class NAVValuationEngine(BaseValuationEngine):
    """Adapter exposing the institutional NAV model through the common engine contract."""

    @property
    def valuation_method(self) -> str:
        return ValuationMethod.NAV.value

    def value(self, entity: Any) -> ValuationResult:
        nav_input = NAVInput(**entity) if isinstance(entity, dict) else entity
        model = NAVModel(nav_input)
        result = model.run_model()
        return ValuationResult(
            entity_name=result.company_name,
            valuation_method=ValuationMethod.NAV,
            valuation_status=(
                ValuationStatus.COMPLETE if result.validation_passed else ValuationStatus.INCOMPLETE
            ),
            enterprise_value=result.gross_asset_value,
            equity_value=result.equity_value,
            diagnostics={
                "share_price": result.implied_share_price,
                "currency": result.currency,
                "warnings": result.warnings,
                "diagnostics": result.diagnostics,
            },
            raw_result=result,
        )

    def evaluate(self, entity: Any) -> ValuationResult:
        """Backward-compatible alias for :meth:`value`."""
        return self.value(entity)


# Backward compatibility alias
NAVEngine = NAVValuationEngine
