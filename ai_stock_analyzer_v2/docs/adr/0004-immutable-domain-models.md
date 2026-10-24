# 0004. Immutable Domain Models in Forecast Subsystem

* Status: Accepted
* Date: 2026-08-02

## Context
The Equity Research Platform requires mathematical determinism and strict data integrity across valuation pipelines (e.g., DCF, Monte Carlo). Mutability in line-item forecasts introduces subtle bugs during scenario analysis, sensitivity modeling, and multi-thread/async execution.

## Decision
We enforce strict immutability and memory optimization across all domain models in `services/forecast/forecast_models.py` using:
1. `@dataclass(frozen=True, slots=True)` decorator configurations.
2. Invariant enforcement in `__post_init__` converting mutable inputs (`list`, `Sequence`) into immutable `tuple` structures via `object.__setattr__`.
3. Standardized sequence protocols (`__len__`, `__getitem__`, `__iter__`) and explicit property accessors to support uniform downstream consumption.

## Consequences
### Positive
* Thread-safe by default; zero side effects during scenario generation or risk simulations.
* Low memory overhead per object instance due to `__slots__`.
* Guaranteed structural determinism from forecast generation through DCF engine consumption.

### Negative / Trade-offs
* Requires creating new dataclass instances rather than mutating fields in place.
* Slight CPU overhead during `__post_init__` tuple conversion on instantiation.