from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from core.enums import ValuationMethod
from services.financials.financial_statement import FinancialStatements


@runtime_checkable
class ValuationEngineProtocol(Protocol):
    method: ValuationMethod

    def calculate(self, valuation_input: Any) -> Any: ...


@runtime_checkable
class MarketDataProviderProtocol(Protocol):
    provider_name: str

    def get_live_price(self, ticker: str) -> float: ...
    def get_historical_prices(self, ticker: str, days: int = 365) -> list[float]: ...
    def get_risk_free_rate(self) -> float: ...


@runtime_checkable
class FinancialRepositoryProtocol(Protocol):
    def store(self, fs: FinancialStatements) -> None: ...
    def get(self, company_name: str, fiscal_year: str) -> FinancialStatements: ...
    def clear(self) -> None: ...
