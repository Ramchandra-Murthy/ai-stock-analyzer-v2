# Fibonacci-Gann walk-forward stability summary

Use `summarize_walk_forward(folds)` from
`modules.fibonacci_gann.stability` after running the existing chronological
walk-forward evaluator. It summarizes:

- Number of folds, test candles, and trades.
- Percentage and count of profitable folds.
- Mean, median, and worst fold return.
- Mean and worst fold maximum drawdown.
- A warning flag when total trades are below a configurable minimum (default 10).

## Interpretation

This is a descriptive stability summary, not a compounded equity curve. Each
fold in the current evaluator starts from the configured capital independently.
Do not add fold returns together and interpret the sum as a portfolio return.
The caller must ensure the folds belong to the intended walk-forward evaluation
and understand whether test windows overlap when a step size smaller than the
test size was selected.

A positive mean return can hide losing folds; inspect the median, worst fold,
profitable-fold percentage, and drawdowns together. The minimum-trade flag is a
sample-size warning, not a statistical significance test. Synthetic tests only
verify software behavior and do not demonstrate trading profitability.

This remains a research-only utility with no live market-data fetching,
Streamlit integration, or broker execution.
