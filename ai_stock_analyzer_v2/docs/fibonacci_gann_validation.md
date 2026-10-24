# Fibonacci/Gann validation harness

This is a deterministic research utility in `modules/fibonacci_gann/validation.py`.
It is deliberately separate from Streamlit, live market-data providers, and broker
execution.

## How it avoids a common look-ahead error

- `build_causal_signals` calls the signal function once per candle and passes only
  the history prefix available at that candle's close.
- A signal for candle *i* is handed to the existing backtester, which enters no
  earlier than candle *i + 1*'s open.
- The signal function receives the current case's assumptions but no future candles.
  Keep it deterministic and do not have it fetch external/live data.
- Existing backtest rules handle stop/target collisions conservatively (stop first)
  and account for configured cost and slippage assumptions.

## Parameter sensitivity

Create multiple `ValidationCase` values with different stop distances,
reward/risk assumptions, or cost estimates, then call
`evaluate_parameter_sensitivity(candles, cases, signal_function)`. All cases use
the same chronologically ordered candle sequence. The result reports the existing
backtest metrics for each case; it does not select a profitable setting automatically.

Example:

```python
from modules.fibonacci_gann.backtest import BacktestConfig
from modules.fibonacci_gann.validation import (
    ValidationCase,
    evaluate_parameter_sensitivity,
)

cases = (
    ValidationCase("baseline", BacktestConfig()),
    ValidationCase(
        "higher-cost",
        BacktestConfig(round_trip_cost_per_unit=0.25, slippage_per_unit_per_side=0.1),
    ),
)
# Supply your fixed Candle sequence and a causal signal function:
# outcomes = evaluate_parameter_sensitivity(candles, cases, signal_function)
```

## Risk and limitations

The harness rejects a per-trade loss ceiling larger than starting capital. The
backtester sizes whole units against the configured estimated risk and capital
limits. Real losses can exceed estimates because of gaps, liquidity, fees, taxes,
and slippage. This is long-only share-style research, not options-lot sizing.

Tests use a tiny fixed synthetic OHLC sample only. Synthetic fixtures validate
software behavior, not market performance. Before interpreting strategy results,
use timestamped, appropriately sourced historical data, keep development and
out-of-sample periods separate, include realistic costs, and compare against a
simple baseline. Parameter sensitivity is a diagnostic, not proof of robustness.
No live data is fetched and no orders are placed.
