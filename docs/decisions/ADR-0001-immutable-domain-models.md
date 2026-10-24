# ADR-0001: Immutable Domain Models & Protocol-Based Engines

* **Status**: Accepted
* **Context**: Financial forecasting requires absolute determinism, thread safety, and transparent state auditing across valuation and reporting pipelines. Mutable data objects risk side-effect pollution in multi-threaded portfolio simulations.
* **Decision**: All domain models must be implemented as frozen, slotted Python `dataclasses` with strict type enforcement. Algorithms must adhere to strict `Protocol` interfaces using pure functions.
* **Consequences**: Zero mutation side-effects, O(1) construction overhead, full round-trip dictionary serialization, and complete test isolation.