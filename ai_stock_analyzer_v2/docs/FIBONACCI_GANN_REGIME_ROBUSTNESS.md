# Fibonacci–Gann Market-Regime Robustness

This research-only utility compares a fixed signal series across historical
windows labelled by the caller, such as trending, sideways, and volatile periods.

## Scope and assumptions

- No live market-data fetching, broker connection, order submission, or Streamlit integration.
- The caller must choose and document regime labels and date/index boundaries. The
  module does not classify regimes automatically or claim the labels are objective.
- Windows are half-open index ranges (start, end), with end exclusive; they must
  contain at least two candles and may not overlap.
- Each window is simulated independently from the supplied backtest configuration.
  Returns are not compounded and should not be interpreted as one portfolio curve.
- Existing backtest assumptions apply, including next-bar-open entry and conservative
  stop-first handling when stop and target are both touched in one candle.
- Provide realistic fees, taxes, and slippage in BacktestConfig; costs are assumptions,
  not a guarantee of actual execution costs.

## Example

    from modules.fibonacci_gann.backtest import BacktestConfig
    from modules.fibonacci_gann.regime_robustness import evaluate_regime_robustness

    results = evaluate_regime_robustness(
        candles,
        signals,
        BacktestConfig(
            capital=10_000,
            max_loss_per_trade=500,
            stop_distance=5,
            round_trip_cost_per_unit=0.5,
            slippage_per_unit_per_side=0.25,
        ),
        regimes={
            "trending": (0, 100),
            "sideways": (100, 200),
            "volatile": (200, 300),
        },
    )
    for item in results:
        print(item.regime, item.result.total_return_pct,
              item.result.max_drawdown_pct, len(item.result.trades))

Use only chronological, historically justified windows. Do not tune the strategy on
the same windows used to report final performance. This output is diagnostic, not
evidence that a strategy will be profitable in live trading.
