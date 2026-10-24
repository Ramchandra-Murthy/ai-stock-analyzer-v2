# Fibonacci-Gann Research Lab UI

The `pages/Fibonacci_Gann_Research_Lab.py` page exposes the research-only backtest, parameter sensitivity, and caller-labelled regime robustness helpers.

## Input
Upload a chronological CSV with columns `timestamp,open,high,low,close,signal`. Signals must be true/false or 1/0. Signal values are treated as known at bar close, with entry no earlier than the next bar's open.

## Analysis
- Runs the baseline backtest using visible user-selected capital, loss budget, stop distance, reward/risk, costs, and slippage assumptions.
- Compares two deterministic parameter variants against the same uploaded candles and signals.
- Optionally evaluates non-overlapping, caller-labelled regime windows using zero-based half-open index ranges.
- Shows a baseline trade ledger and provides CSV export.

## Safety and scope
This page uses only user-uploaded data and makes no live market-data requests. It does not generate buy/sell recommendations, infer regimes, optimize parameters, connect to a broker, or submit orders. Results are hypothetical; inspect data quality, signal timing, fees, slippage, sample size, and out-of-sample performance before interpreting them.
