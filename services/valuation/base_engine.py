from __future__ import annotations

"""
==========================================================
BASE VALUATION ENGINE
Module  : base_engine
Version : V1.0
==========================================================

Defines the abstract interface that every valuation engine
must implement.

Examples:
    • DCF Engine
    • NAV Engine
    • Market Value Engine
    • Comparable Company Engine
    • Book Value Engine
"""

from abc import ABC, abstractmethod
from typing import Any

from services.valuation.models import ValuationResult


class BaseValuationEngine(ABC):
    """
    Abstract base class for all valuation engines.
    """

    @property
    @abstractmethod
    def valuation_method(self) -> str:
        """
        Returns the valuation methodology identifier.

        Examples:
            DCF
            NAV
            MARKET
            BOOK_VALUE
        """
        raise NotImplementedError

    @abstractmethod
    def value(
        self,
        entity: Any,
    ) -> ValuationResult:
        """
        Performs valuation and returns a standardized
        ValuationResult.
        """
        raise NotImplementedError

    @property
    def engine_name(self) -> str:
        """
        Human-readable engine name.
        """
        return self.__class__.__name__

    def __repr__(self) -> str:
        return f"{self.engine_name}" f"(method={self.valuation_method})"
