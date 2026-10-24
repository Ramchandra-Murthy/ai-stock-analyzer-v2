# Forecast Subsystem (`services/forecast`)

## Overview
The Forecast Subsystem is responsible for generating deterministic financial projections (Revenue, Net Income, Capital Expenditures, Depreciation, Working Capital, and Tax Rates) over designated multi-year horizons based on historical financial metrics.

## Architecture & Standards
- **Immutable Domain Models:** Implemented using frozen data classes with memory slot optimization.
- **Contract-Driven Design:** Clear boundaries enforced between input contracts, algorithmic processors, and output packages.
- **Serialization Ready:** Full bidirectional dictionary serialization supporting storage and API transport.