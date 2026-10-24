# Contributing to AI Stock Analyzer (AIERP)

Thank you for your interest in contributing to the AI Institutional Equity Research Platform! Please follow these standards to ensure a smooth contribution process.

## Development Workflow
1. Fork the repository and create your feature branch from `develop` (`feature/your-feature-name`).
2. Ensure Python 3.13+ is installed.
3. Install development dependencies: `pip install -e ".[dev]"`
4. Implement your feature along with comprehensive unit tests in `tests/`.
5. Run code quality checks locally:
   - `ruff check .`
   - `black --check .`
   - `mypy .`
   - `pytest`
6. Submit a Pull Request targeting `develop`.

