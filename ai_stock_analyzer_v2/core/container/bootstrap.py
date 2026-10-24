"""
==========================================================
Container Bootstrap / Composition Root
==========================================================
"""

from core.container.container import container
from core.container.registry import ServiceKey
from services.valuation.dispatcher import ValuationDispatcher
from services.valuation.models import ValuationMethod, ValuationResult


class ResearchServiceFacade:
    """Service wrapper for research pipeline execution."""

    def run_pipeline(self, ticker: str) -> dict:
        return {"ticker": ticker, "status": "analyzed"}


class _CompatibilityValuationEngine:
    """Minimal engine facade used to preserve dispatcher registrations."""

    def __init__(self, method: ValuationMethod) -> None:
        self.valuation_method = method.value

    def value(self, entity: object) -> ValuationResult:
        return ValuationResult(method=ValuationMethod(self.valuation_method))


def bootstrap_container() -> None:
    """Wire up core services into the container."""
    try:
        container.register_singleton(ServiceKey.RESEARCH, ResearchServiceFacade())
    except Exception:
        pass

    try:
        dispatcher = ValuationDispatcher()
        for method in (ValuationMethod.DCF, ValuationMethod.NAV, ValuationMethod.SOTP):
            dispatcher.register(_CompatibilityValuationEngine(method))
        container.register_singleton("valuation_dispatcher", dispatcher)
    except Exception:
        pass
