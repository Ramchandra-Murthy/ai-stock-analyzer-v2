"""
==========================================================
Dependency Injection Container Exceptions
==========================================================
"""


class ContainerError(Exception):
    """Base exception for the DI container."""

    pass


class ServiceNotFoundError(ContainerError):
    """Raised when a requested service has non-existent registration."""

    pass


class DuplicateServiceError(ContainerError):
    """Raised when attempting to register the same service twice."""

    pass
