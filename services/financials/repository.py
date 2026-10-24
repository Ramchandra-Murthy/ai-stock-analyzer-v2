from __future__ import annotations

from core.exceptions import RepositoryError
from core.logger import logger
from services.financials.financial_statement import FinancialStatements


class FinancialStatementRepository:
    """In-memory singleton repository for validated FinancialStatements."""

    _instance: FinancialStatementRepository | None = None

    def __new__(cls) -> FinancialStatementRepository:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._storage = {}
        return cls._instance

    def store(self, fs: FinancialStatements) -> None:
        """Stores a validated FinancialStatements object using composite key (company_name, fiscal_year)."""
        key = (fs.company_name.lower().strip(), fs.fiscal_year.upper().strip())
        self._storage[key] = fs
        logger.info(f"[{fs.ticker}] Stored financial statements under key: {key}")

    def get(self, company_name: str, fiscal_year: str) -> FinancialStatements:
        """Retrieves FinancialStatements from storage or raises RepositoryError."""
        key = (company_name.lower().strip(), fiscal_year.upper().strip())
        fs = self._storage.get(key)
        if not fs:
            error_msg = f"Financial statements not found for Company: '{company_name}', Period: '{fiscal_year}'"
            logger.error(f"[REPOSITORY_ERROR] {error_msg}")
            raise RepositoryError(error_msg)

        logger.info(
            f"[{fs.ticker}] Successfully retrieved financial statements for period {fiscal_year}"
        )
        return fs

    def clear(self) -> None:
        """Clears all stored entries (primarily for test teardowns)."""
        self._storage.clear()
        logger.info("[REPOSITORY] Storage cleared successfully.")


def get_repository() -> FinancialStatementRepository:
    """Helper accessor for global repository instance."""
    return FinancialStatementRepository()
