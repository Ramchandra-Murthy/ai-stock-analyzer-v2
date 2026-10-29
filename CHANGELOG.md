# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Advanced Portfolio Lab page: efficient frontier, Black-Litterman, tail risk (Cornish-Fisher VaR), Monte Carlo paths and stress tests, backed by `algorithmic_trading/portfolio_advanced.py`, `risk_advanced.py` and `lab_inputs.py` with unit tests.
- `run_app.sh` launcher; the dev container now uses Python 3.13, installs from `uv.lock` and starts the Streamlit app on open.

### Removed
- Duplicated nested `ai_stock_analyzer_v2/` copy of the project (about 1,100 files); the repository root is the single source.

### Added (earlier)
- Repository foundation (M0) including directory structure, CI/CD workflows, governance documents, and tool configurations.

