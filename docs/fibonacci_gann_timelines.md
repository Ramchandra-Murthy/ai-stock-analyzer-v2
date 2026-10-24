# Fibonacci timeline calculation helper

## Purpose

This research helper projects future bar positions from an explicitly supplied
anchor bar using positive Fibonacci-number intervals. Its default intervals are
1, 2, 3, 5, 8, 13, 21, 34, 55, and 89 bars. For anchor index A and interval n,
the projected bar index is:

    projected index = A + n

The caller chooses the anchor and the bar-index convention. The helper does
not infer a significant high or low, convert bars to calendar dates, inspect
market data, generate trading signals, or submit broker orders.

## Source alignment and limits

Fibonacci time analysis uses Fibonacci-number intervals as temporal reference
points. This implementation deliberately provides only transparent interval
arithmetic. It should not be treated as a complete reproduction of every
timeline construction or chart interpretation in George Alexander MacLean's
*Fibonacci and Gann Applications in Financial Markets*. Verify any specific
book figure, anchor-selection rule, or calendar-time convention against the
relevant source passage before claiming exact source fidelity.

A projected bar is a time window to observe, not a guaranteed turning point,
price target, direction forecast, or trade signal. Bar counts can differ from
calendar time because of weekends, holidays, and session gaps. Unit tests
verify arithmetic and input validation only; they do not establish predictive
value.
