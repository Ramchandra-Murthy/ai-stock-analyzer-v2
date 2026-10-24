# Explicit Gann price-range divisions

## Purpose

This research helper divides an explicitly supplied price range into equal
intervals. For start price (P_0), end price (P_1), division count (n),
and index (i), the level is:

    fraction = i / n
    level = P0 + (P1 - P0) * fraction

The default is eight divisions, returning nine levels at fractions 0/8
through 8/8. For example, dividing 80 to 160 into eighths yields levels from
80 through 160 in increments of 10. A descending range is also supported;
the supplied endpoint order is preserved.

## Interpretation and limitations

- The range endpoints are supplied explicitly. The helper does not select
  swing highs/lows or determine whether a range is meaningful.
- Equal divisions are a configurable arithmetic convention, not a claim that
  this is the only Gann division method or a complete reproduction of any
  book's method.
- Levels are reference values, not trading signals, targets, support,
  resistance, or predictions validated by market data.
- The helper does not access live data, generate signals, run backtests, or
  place broker orders.
- Unit tests verify arithmetic and input validation only. No predictive
  performance or profitability is claimed.
