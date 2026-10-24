# Fibonacci & Gann Strategy Lab

## Status

This remains an isolated analysis-only module. It is not connected to Streamlit pages, market-data providers, scanners, portfolio services, or broker APIs. No orders are submitted.

## Current calculations and safeguards

- Fibonacci retracements for an upward swing: `H - ratio * (H - L)` at 23.6%, 38.2%, 50%, 61.8%, and 78.6%.
- Fibonacci upside extensions beyond the swing high: `H + ratio * (H - L)` at 1.000x, 1.272x, 1.618x, 2.000x, and 2.618x.
- Gann eighths: nine levels from 0/8 through 8/8, inclusive.
- `Decimal` arithmetic and validation reject non-finite, non-positive, or incorrectly ordered swing prices.
- OHLC integrity and freshness checks reject empty, stale, future-dated, unordered, timezone-naive, or internally inconsistent candle data.
- Confirmed swing detection requires both left- and right-side candles; the latest right-side window is not emitted as confirmed, reducing look-ahead bias. Equal highs/lows are excluded rather than arbitrarily selecting a plateau.
- The confluence engine groups nearby calculated levels using an explicit absolute price tolerance. It reports the zone's low, high, midpoint, and contributing level family/labels. Single levels are not reported as confluence; exact overlaps can be found with zero tolerance.
- The integration test validates OHLC bars, detects confirmed pivots, then passes a confirmed low/high pair into confluence analysis. This is a test workflow only; no live-data connection is added.
- Position sizing floors quantity to whole units and takes the tighter of the available-capital limit and estimated-loss limit. Estimated per-unit risk includes the entry-to-stop distance plus a caller-supplied estimate for round-trip fees and slippage. It rejects invalid inputs and refuses a size when one unit breaches the loss ceiling.
- The historical backtest helper accepts caller-provided boolean signals. A signal is evaluated at bar close and entry occurs no earlier than the next bar open. It simulates one long position at a time and reports net trade P&L, win rate, expectancy, profit factor, return, and maximum drawdown.

The 50% retracement is a commonly used market convention, not a Fibonacci ratio. Extension conventions differ between charting tools; this module explicitly uses the beyond-high formula documented above. Swing detection expects callers to validate their OHLC bars first. Confluence is descriptive geometry, not statistical evidence that a level will hold.

## Examples

```python
from modules.fibonacci_gann import calculate_position_size, find_confluence_zones

zones = find_confluence_zones(800, 1000, tolerance="2")
for zone in zones:
    print(zone.low, zone.high, zone.center)

# Illustrative long-position sizing; costs are estimated, not broker-verified.
size = calculate_position_size(
    entry_price="100",
    stop_price="95",
    capital="10000",
    max_loss="500",
    cost_per_unit="1",
)
print(size.quantity, size.estimated_loss, size.capital_required)
```

## Historical backtest assumptions and limits

`modules/fibonacci_gann/backtest.py` provides a deterministic research harness. Pass chronological `Candle` objects and a same-length boolean signal sequence. Signals must be produced without future data; the engine shifts execution to the next candle's open to avoid filling at the signal candle's close. If a candle touches both stop and target, the stop is assumed to occur first. A gap below the stop is filled at the candle open, not the stop price. Slippage is charged adversely on entry and exit; supply a realistic round-trip per-unit fee/tax estimate. Position sizing uses the configured ₹10,000 capital and ₹500 maximum estimated loss by default, but this is an illustrative budget, not a promise that realized losses cannot exceed ₹500.

This first version is a simulation primitive, not a complete validated Fibonacci/Gann strategy. It does not fetch data, generate strategy signals, model partial fills, dividends, corporate actions, short positions, options, or exchange-specific charges. Historical results are not evidence of future performance. Add walk-forward and out-of-sample validation before drawing conclusions.

## Risk note

A plotted level or confluence zone is not a buy/sell signal and does not demonstrate a profitable edge. For options, analyse the underlying first; option premium, implied volatility, time decay, spread, and lot size can make a technically plausible underlying setup unsuitable. Never trade when the estimated maximum loss exceeds the configured limit. The conservative example budget is ₹10,000 trading capital and ₹500 maximum acceptable loss per trade including costs.
