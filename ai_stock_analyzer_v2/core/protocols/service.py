from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DomainServiceProtocol(Protocol):
    """Protocol for stateless domain services."""

    def execute(self, *args: Any, **kwargs: Any) -> Any: ...
