# Core Financial Domain Kernel

The `core` package serves as the immutable, type-safe foundation for the AI Institutional Equity Research Platform. It adheres strictly to Domain-Driven Design (DDD) and Clean Architecture principles.

## Package Modules

1. **`core.primitives`**: Immutable numeric and financial value objects backed by `decimal.Decimal` for maximum precision (Money, Percentage, Quantity, Currency).
2. **`core.value_objects`**: Temporal and fiscal domain objects (FiscalYear, FiscalQuarter, FiscalPeriod, DateRange).
3. **`core.identifiers`**: Strongly typed market and security identifiers (CompanySymbol, ISIN, ExchangeCode, Sector, Industry).

## Design Rules
- All domain objects inherit from `ValueObject` and are immutable (`frozen=True`).
- Financial calculations strictly avoid floating-point inaccuracies by utilizing `Decimal`.
- Complete test coverage across all sub-modules.

