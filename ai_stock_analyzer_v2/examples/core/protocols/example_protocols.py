from __future__ import annotations

from core.protocols import RepositoryProtocol


def run_example() -> None:
    print("--- CORE-005: Protocols & Interfaces Example ---")
    print(f"RepositoryProtocol runtime checkable: {not isinstance(object(), RepositoryProtocol)}")


if __name__ == "__main__":
    run_example()
