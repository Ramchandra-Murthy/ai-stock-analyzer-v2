import pytest

from core.container.container import ServiceContainer
from core.container.exceptions import ContainerError, DuplicateServiceError


def test_register_and_resolve() -> None:
    container = ServiceContainer()
    obj = object()
    container.register("service", obj)
    assert container.resolve("service") is obj


def test_duplicate_registration() -> None:
    container = ServiceContainer()
    container.register("x", object())
    with pytest.raises(DuplicateServiceError):
        container.register("x", object())


def test_unknown_service() -> None:
    container = ServiceContainer()
    with pytest.raises(ContainerError):
        container.resolve("missing")


def test_clear_container() -> None:
    container = ServiceContainer()
    container.register("x", object())
    container.clear()
    with pytest.raises(ContainerError):
        container.resolve("x")
