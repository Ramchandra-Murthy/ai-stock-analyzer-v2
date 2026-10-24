# AI Institutional Equity Research Platform
## Software Engineering Manual (SEM)
**Version**: 1.0 | **Applies To**: Entire Repository

---

### 1. Documentation Hierarchy
* **Repository Level**: Master README & Roadmap
* **Governance Level**: Software Engineering Manual (SEM)
* **Architecture Level**: Architecture Decision Records (ADR)
* **Specification Level**: Engineering Specifications (ES)
* **Code Level**: Type hints, Docstrings, and Module Readmes

### 2. Coding & Quality Standards
* **Max Function Length**: 50 lines
* **Max Class Length**: 200 lines
* **Max File Length**: 600 lines
* **Cyclomatic Complexity**: $\le 10$ per function
* **Typing & Docs**: 100% explicit type hints and docstrings required for all public symbols.
* **Dependencies**: Standard library preferred; third-party packages must be explicitly vetted and approved.

### 3. Exception Hierarchy
All domain-specific errors must inherit from module base exceptions (e.g., `ForecastError`, `CapitalError`, `ValuationError`). Raw built-in exceptions like `ValueError` should be wrapped in domain validation errors.

### 4. Logging Policy
* **Models**: No logging (pure domain).
* **Algorithms**: Optional debug logging.
* **Services**: Structured `INFO`, `WARN`, `ERROR` logging.
* **API / CLI**: Request/Response and user-facing error reporting.

### 5. Performance Budgets
* Forecast Engine Build: $< 50\text{ ms}$
* DCF Valuation: $< 20\text{ ms}$
* WACC Calculation: $< 5\text{ ms}$
* Portfolio Valuation (100 stocks): $< 5\text{ s}$

### 6. Definition of Done
A feature is complete only if implementation passes Black, Ruff, MyPy, PyTest (100% coverage on core logic), review approval, and CI pipeline checks.