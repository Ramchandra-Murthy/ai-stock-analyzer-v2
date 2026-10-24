# Fibonacci-Gann transaction-cost sensitivity

Use `evaluate_cost_sensitivity` from
`modules.fibonacci_gann.cost_sensitivity` to rerun a fixed signal series across
combinations of round-trip per-unit costs and per-side slippage assumptions.

    rows = evaluate_cost_sensitivity(
        candles,
        signals,
        base_config,
        round_trip_costs=[0, 0.5, 1.0],
        slippage_per_side_values=[0, 0.25, 0.5],
    )

Each output row contains the cost assumptions and the normal backtest result.
The function keeps signals fixed and changes only execution-cost assumptions.
Quantity can also change because the existing backtester sizes positions using
the configured risk allowance and modeled costs.

Use realistic, instrument-specific cost estimates when available. Zero-cost
scenarios are a baseline, not a realistic default. This sensitivity analysis
does not establish profitability, predict future slippage, or model signal
changes caused by execution costs. It is research-only and has no live data,
Streamlit, or broker integration.
