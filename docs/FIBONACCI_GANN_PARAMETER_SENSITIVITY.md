# Fibonacci–Gann Parameter Sensitivity

## Purpose
Compare a fixed set of signals across explicitly named backtest configurations. This helps reveal whether reported outcomes depend heavily on a single choice of stop distance, reward/risk ratio, cost, slippage, or sizing assumptions.

## Usage
Call `evaluate_parameter_sensitivity(candles, signals, variants)`, where `variants` maps readable labels to `BacktestConfig` objects. Keep the same candles and signals for every variant so the comparison changes assumptions rather than data or signal timing.

## Interpretation
- Each configuration is backtested independently from its own starting capital.
- Results are returned in the order variants were supplied; they are not compounded.
- This helper does not automatically select a best configuration, infer regimes, fetch market data, or place orders.
- A stable result across a few variants is not proof of profitability. Include out-of-sample testing, realistic costs/slippage, adequate trade counts, and benchmark comparisons before drawing conclusions.
- Parameter variants should be chosen before examining outcomes where possible to reduce selection bias.

## Scope
Research-only Python module and tests. No Streamlit integration, live-data calls, broker connections, or execution.
