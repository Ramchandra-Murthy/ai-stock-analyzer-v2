# Fibonacci-Gann benchmark diagnostics

The isolated research package provides compare_with_buy_and_hold(candles, result)
in modules/fibonacci_gann/benchmark.py. It reports strategy return, buy-and-hold
close-to-close return, excess return, both drawdowns, trade count, and whether
the number of trades is below a configurable minimum (default 10).

## Example

    from modules.fibonacci_gann.benchmark import compare_with_buy_and_hold

    comparison = compare_with_buy_and_hold(test_candles, backtest_result, minimum_trades=10)
    print(comparison.excess_return_pct, comparison.insufficient_trades)

Pass exactly the same out-of-sample candles used for the backtest result. The
function cannot verify that the result came from those candles, so matching the
test window is the caller's responsibility. For walk-forward analysis, compare
each fold independently; do not treat independently capitalized folds as one
compounded portfolio.

The buy-and-hold calculation uses first and last close and does not include
dividends, fees, taxes, or slippage. It is a simple reference, not a fully
investable total-return benchmark. Positive excess return on a small sample is
not evidence of a reliable edge. The minimum-trade flag is a warning only, not
a statistical significance test.

This is a research-only utility. It does not fetch market data, connect to
Streamlit, place broker orders, or establish future profitability. Historical
drawdowns and estimated per-trade risk do not cap losses in live markets.
