from __future__ import annotations

from typing import Any

from core.protocols import DomainServiceProtocol, RepositoryProtocol


class DummyEntity:
    def __init__(self, uid: str) -> None:
        self.uid = uid


class DummyRepository:
    def get_by_id(self, identifier: Any) -> DummyEntity | None:
        return DummyEntity(identifier)

    def save(self, aggregate: DummyEntity) -> None:
        pass


def test_repository_protocol() -> None:
    repo = DummyRepository()
    assert isinstance(repo, RepositoryProtocol)


def test_domain_service_protocol() -> None:
    class DummyService:
        def execute(self, value: int) -> int:
            return value * 2

    service = DummyService()
    assert isinstance(service, DomainServiceProtocol)
