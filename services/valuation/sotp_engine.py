from __future__ import annotations

from typing import Any

from services.valuation.base_engine import BaseValuationEngine
from services.valuation.models import ValuationMethod, ValuationResult, ValuationStatus


class SOTPValuationEngine(BaseValuationEngine):
    """Sum-of-the-parts valuation adapter with dispatcher compatibility."""

    def __init__(self, dispatcher: Any | None = None) -> None:
        self.dispatcher = dispatcher

    @property
    def valuation_method(self) -> str:
        return ValuationMethod.SOTP.value

    def value(
        self,
        entity: Any = None,
        *,
        entities: list[dict[str, Any]] | None = None,
        net_debt: float = 0.0,
        shares_outstanding: float = 1.0,
        holdco_discount: float = 0.0,
    ) -> ValuationResult:
        """Value one entity or aggregate a collection of segment entities."""
        if entities is None:
            return self._value_single(entity)

        component_results: list[ValuationResult] = []
        enterprise_value = 0.0
        equity_value = 0.0

        for item in entities:
            method = str(item.get("valuation_method", "")).upper()
            if self.dispatcher is None:
                result = self._pending_component(item)
            else:
                result = self.dispatcher.value(method, item)
            component_results.append(result)
            enterprise_value += result.enterprise_value
            equity_value += result.equity_value

        equity_value -= net_debt
        equity_value *= 1.0 - holdco_discount
        implied_share_price = equity_value / shares_outstanding if shares_outstanding else 0.0

        return ValuationResult(
            method=ValuationMethod.SOTP,
            entity_name="SOTP",
            valuation_status=ValuationStatus.SUCCESS,
            enterprise_value=enterprise_value,
            equity_value=equity_value,
            implied_share_price=implied_share_price,
            component_results=component_results,
            diagnostics={"net_debt": net_debt, "holdco_discount": holdco_discount},
        )

    def evaluate(self, data: Any) -> ValuationResult:
        """Backward-compatible alias for :meth:`value`."""
        return self.value(data)

    def _value_single(self, entity: Any) -> ValuationResult:
        if self.dispatcher is not None and isinstance(entity, dict):
            method = str(entity.get("valuation_method", "")).upper()
            return self.dispatcher.value(method, entity)
        return self._pending_component(entity)

    @staticmethod
    def _pending_component(entity: Any) -> ValuationResult:
        name = entity.get("segment_name", "Unknown") if isinstance(entity, dict) else str(entity)
        return ValuationResult(
            method=ValuationMethod.SOTP,
            entity_name=name,
            valuation_status=ValuationStatus.PENDING,
            enterprise_value=0.0,
            equity_value=0.0,
            diagnostics={"error": "No valuation dispatcher is configured for this component."},
        )


# Backward compatibility alias
SOTPEngine = SOTPValuationEngine
