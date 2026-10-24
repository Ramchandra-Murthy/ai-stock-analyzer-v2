# Fibonacci/Gann walk-forward validation

`modules/fibonacci_gann/walk_forward.py` adds chronological out-of-sample folds
to the isolated research lab. It is not connected to Streamlit, live market-data
providers, or broker execution.

## Usage

```python
from modules.fibonacci_gann.backtest import BacktestConfig
from modules.fibonacci_gann.walk_forward import evaluate_walk_forward

folds = evaluate_walk_forward(
    candles,
    signal_function,
    BacktestConfig(
        capital=10_000,
        max_loss_per_trade=500,
        round_trip_cost_per_unit=0.25,
        slippage_per_unit_per_side=0.10,
    ),
    initial_train_size=100,
    test_size=20,
    step_size=20,
)
for fold in folds:
    print(fold.test_start, fold.test_end, fold.result.total_return_pct)
```

## Method and limitations

- The initial history period ends before the first test window.
- Test windows proceed chronologically. The default step equals the test size,
  so test windows do not overlap; a smaller step intentionally creates overlap.
- For every test candle, the signal callback receives the full candle prefix
  ending at that candle's close and never receives a future candle.
- The existing backtester enters on the next test candle's open and applies its
  conservative stop/target and cost assumptions.
- Each fold is simulated independently from the configured starting capital.
  Fold results are not compounded and must not be interpreted as a continuous
  portfolio equity curve.
- This utility does not fit or retrain a model. The caller must keep any
  parameter selection or model fitting confined to the training history; do not
  choose parameters by inspecting test-fold results.
- The backtest's configured per-trade risk is an estimate. Gaps, liquidity,
  fees, taxes, and slippage can make realized losses larger. This is long-only
  share-style research, not options-lot sizing.

Use properly sourced, timestamped historical candles and realistic costs. The
included synthetic tests verify software behavior only, not profitability or
future performance. No live data is fetched and no orders are placed.
