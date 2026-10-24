from __future__ import annotations

from typing import Any

from services.valuation.base_engine import BaseValuationEngine
from services.valuation.dcf import DCFInput, DCFModel
from services.valuation.models import ValuationMethod, ValuationResult, ValuationStatus


class DCFValuationEngine(BaseValuationEngine):
    """Adapter exposing the institutional DCF model through the common engine contract."""

    @property
    def valuation_method(self) -> str:
        return ValuationMethod.DCF.value

    def value(self, entity: Any) -> ValuationResult:
        dcf_input = DCFInput(**entity) if isinstance(entity, dict) else entity
        model = DCFModel(dcf_input)
        result = model.run_model()
        return ValuationResult(
            entity_name=result.company_name,
            valuation_method=ValuationMethod.DCF,
            valuation_status=(
                ValuationStatus.COMPLETE if result.validation_passed else ValuationStatus.INCOMPLETE
            ),
            enterprise_value=result.enterprise_value,
            equity_value=result.equity_value,
            diagnostics={
                "share_price": result.implied_share_price,
                "currency": result.currency,
                "warnings": result.warnings,
            },
            raw_result=result,
        )

    def evaluate(self, entity: Any) -> ValuationResult:
        """Backward-compatible alias for :meth:`value`."""
        return self.value(entity)


# Backward compatibility alias
DCFEngine = DCFValuationEngine
