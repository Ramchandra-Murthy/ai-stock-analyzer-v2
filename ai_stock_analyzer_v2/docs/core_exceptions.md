# Core Exception Framework

## Overview
The `core.exceptions` package defines a structured exception hierarchy for the AI Institutional Equity Research Platform. All custom exceptions inherit from the base `AIERPError` class.

## Exception Hierarchy
- `AIERPError`: Root exception for all platform errors.
  - `DomainError`: Business logic and domain rule failures.
    - `ValidationError`: Input parameters violating financial constraints.
    - `CalculationError`: Numerical or modeling convergence failures.
  - `SerializationError`: Data mapping or JSON export failures.
  - `InfrastructureError`: External connectivity or service failures.

