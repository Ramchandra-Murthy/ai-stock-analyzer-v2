from __future__ import annotations

from typing import Any

from services.valuation.base_engine import BaseValuationEngine
from services.valuation.models import ValuationResult


class ValuationDispatcher:
    """Registry that routes valuation requests to registered engines."""

    def __init__(self) -> None:
        self._engines: dict[str, BaseValuationEngine] = {}

    def list_supported_methods(self) -> list[str]:
        """Return registered valuation method names."""
        return list(self._engines.keys())

    def register_engine(self, name: str, engine: BaseValuationEngine) -> None:
        """Register an engine under an explicit method name."""
        self._engines[name.upper()] = engine

    def register(self, engine: BaseValuationEngine) -> None:
        """Register an engine using its declared valuation method."""
        method_key = engine.valuation_method.upper()
        self._engines[method_key] = engine

    def get_engine(self, method: str) -> BaseValuationEngine:
        """Retrieve an engine by valuation method."""
        key = method.upper()
        try:
            return self._engines[key]
        except KeyError as exc:
            raise KeyError(f"No valuation engine registered for method: '{method}'.") from exc

    def value(self, method: str, entity: Any) -> ValuationResult:
        """Execute valuation using the requested method."""
        engine = self.get_engine(method)
        return engine.value(entity)

    def dispatch(self, method: str, entity: Any) -> ValuationResult:
        """Backward-compatible alias for :meth:`value`."""
        return self.value(method, entity)
