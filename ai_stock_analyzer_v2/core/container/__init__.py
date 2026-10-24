"""Public dependency-injection container API."""

from core.container.bootstrap import bootstrap_container
from core.container.container import ServiceContainer, container
from core.container.exceptions import ContainerError, DuplicateServiceError, ServiceNotFoundError
from core.container.registry import ServiceKey

__all__ = [
    "ContainerError",
    "DuplicateServiceError",
    "ServiceContainer",
    "ServiceKey",
    "ServiceNotFoundError",
    "bootstrap_container",
    "container",
]
