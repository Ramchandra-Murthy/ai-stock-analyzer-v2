"""
Dependency Injection Container Implementation.
"""

from collections.abc import Callable
from typing import Any

from core.container.exceptions import DuplicateServiceError, ServiceNotFoundError


class ServiceContainer:
    def __init__(self) -> None:
        self._singletons: dict[str, Any] = {}
        self._factories: dict[str, Callable[[], Any]] = {}

    def register(self, key: str, instance: Any) -> None:
        """Alias for register_singleton for compatibility."""
        self.register_singleton(key, instance)

    def register_singleton(self, key: str, instance: Any) -> None:
        if key in self._singletons or key in self._factories:
            raise DuplicateServiceError(f"Service '{key}' is already registered.")
        self._singletons[key] = instance

    def register_factory(self, key: str, factory: Callable[[], Any]) -> None:
        if key in self._singletons or key in self._factories:
            raise DuplicateServiceError(f"Service '{key}' is already registered.")
        self._factories[key] = factory

    def resolve(self, key: str) -> Any:
        if key in self._singletons:
            return self._singletons[key]
        if key in self._factories:
            return self._factories[key]()
        raise ServiceNotFoundError(f"Service '{key}' not found in container.")

    def clear(self) -> None:
        self._singletons.clear()
        self._factories.clear()


container = ServiceContainer()
