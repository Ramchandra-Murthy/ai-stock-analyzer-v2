# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Advanced Portfolio Lab page: efficient frontier, Black-Litterman, tail risk (Cornish-Fisher VaR), Monte Carlo paths and stress tests, backed by `algorithmic_trading/portfolio_advanced.py`, `risk_advanced.py` and `lab_inputs.py` with unit tests.
- `run_app.sh` launcher; the dev container now uses Python 3.13, installs from `uv.lock` and starts the Streamlit app on open.
- BSE support across the research pages: Portfolio Optimizer, Risk Dashboard, Momentum Portfolio (NSE or BSE universe), Pairs Research and the Lab now accept `TCS`, `NSE:TCS`, `.NS`/`.BO` tickers and six-digit BSE scrip codes through one resolver (`services/symbol_resolver.py`) and one loader (`services/price_table.py`).
- Data Health page and `services/data_health.py`: per-list coverage for NSE names, BSE scrip codes and BSE names, with advice.
- Minimum-CVaR optimiser and whole-share rebalance planner (`algorithmic_trading/portfolio_tools.py`) in the Advanced Portfolio Lab.

### Fixed
- BSE stocks missing from the watchlist gainers scan: it examined only 8 of 80 curated BSE codes, dropped symbols with no data without saying so, and cached an empty result for five minutes. It now scans 24/48/80 codes concurrently, reports "Scored N of M", never caches an empty scan, and retries a code the provider does not serve under its `NAME.BO` ticker.
- A symbol with no price history no longer blanks the whole table on the research pages; it is named in a warning and the rest are analysed.

### Removed
- Duplicated nested `ai_stock_analyzer_v2/` copy of the project (about 1,100 files); the repository root is the single source.

### Added (foundation)
- Repository foundation (M0) including directory structure, CI/CD workflows, governance documents, and tool configurations.

