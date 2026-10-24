from services.valuation.dcf_engine import DCFEngine
from services.valuation.dispatcher import ValuationDispatcher
from services.valuation.nav_engine import NAVEngine


def get_valuation_dispatcher() -> ValuationDispatcher:
    dispatcher = ValuationDispatcher()
    dispatcher.register(DCFEngine())
    dispatcher.register(NAVEngine())
    return dispatcher


__all__ = [
    "ValuationDispatcher",
    "DCFEngine",
    "NAVEngine",
    "get_valuation_dispatcher",
]
