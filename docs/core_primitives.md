# Core Financial Primitives Architecture

## Motivation
Institutional equity research requires absolute mathematical precision and structural type safety. Standard Python floating-point types (`float`) introduce rounding errors that compound in complex financial models. The `core.primitives` package implements strict, immutable value objects powered by `decimal.Decimal`.

## Design Philosophy
1. **Immutability:** All value objects are frozen (`frozen=True`) dataclasses.
2. **Precision:** Monetary values and percentages enforce decimal arithmetic (`ROUND_HALF_UP`).
3. **Type Safety:** Explicit currency checks prevent cross-currency contamination in arithmetic operations.
4. **Serialization-Ready:** Standard dictionary export methods (`to_dict()`) support downstream API and caching layers.

## Public Types
- `Money`: Currency-aware monetary value.
- `Percentage`: Rate representation with fraction conversion.
- `Quantity`: Share counts and numerical volume.
- `Currency`: ISO 4217 standard enumeration.

