from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DomainServiceProtocol(Protocol):
    pass


@runtime_checkable
class RepositoryProtocol(Protocol):
    pass


@runtime_checkable
class Serializable(Protocol):
    def to_dict(self) -> dict: ...


@runtime_checkable
class Validatable(Protocol):
    def validate(self) -> bool: ...
