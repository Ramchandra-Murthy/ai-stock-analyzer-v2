# Core Types Documentation

The `core/types` package provides immutable, precision-backed foundational value objects for all platform engines.

## Key Principles
1. **Precision:** All monetary and percentage calculations utilize Python's `Decimal` type to prevent float rounding errors.
2. **Immutability:** Value objects use frozen dataclasses, ensuring thread safety and deterministic behavior.
3. **Type Safety:** Strong typing across currencies, share counts, and financial aliases.

