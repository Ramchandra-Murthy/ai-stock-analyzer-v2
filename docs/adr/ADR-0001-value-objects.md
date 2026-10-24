# ADR-0001: Immutable Value Objects for Financial Primitives

## Status
Accepted

## Context
Institutional equity research and financial modeling require absolute precision, deterministic comparison, and freedom from side-effect mutations. Primitive types such as currency amounts, percentages, and identifiers must behave as mathematical values rather than mutable entities.

## Decision
1. All domain primitives inherit from an immutable base `ValueObject` (implemented via frozen dataclasses).
2. Financial amounts utilize `decimal.Decimal` exclusively instead of IEEE 754 floating-point numbers to prevent rounding errors.
3. Custom domain errors (`PrimitiveTypeError`, `CurrencyMismatchError`) are established for precise exception handling.

## Consequences
- Guarantees thread safety and referential transparency across calculations.
- Eliminates subtle floating-point drift in compound financial metrics (e.g., Wairflow, DCF, Multiples).

