# Explicit Gann-style time divisions

## Purpose

This helper divides an explicitly supplied interval of bar positions into equal
fractions. For start position (T0), end position (T1), division count (n), and
index (i), each position is:

    fraction = i / n
    position = T0 + (T1 - T0) * fraction

The default is eight divisions, returning nine positions from fraction 0 to 1.
For example, dividing positions 0 to 80 into eighths yields 0, 10, 20, ... 80.
Descending intervals preserve the supplied endpoint order. Intermediate
positions may be fractional when the interval does not divide into whole bars.

## Interpretation and limitations

- Start and end positions are supplied by the caller; no market-cycle or pivot
  detection is performed.
- Equal interval division is an explicit arithmetic convention, not a claim to
  reproduce every Gann time-counting method or a complete method from a book.
- Returned positions are reference coordinates, not forecasts, dates, signals,
  support/resistance levels, or validated trading opportunities.
- The helper does not fetch market data, infer trading sessions, generate
  signals, run backtests, or place broker orders.
- Unit tests verify arithmetic and input validation only. No predictive
  performance or profitability is claimed.
