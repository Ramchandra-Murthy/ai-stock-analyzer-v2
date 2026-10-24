# Explicit Gann angle level calculations

## Purpose

This research helper evaluates simple straight-line price levels from an
explicit anchor price and bar index. The caller supplies slopes measured in
price units per bar. For anchor price P, anchor bar b₀, target bar b₁, and
slope m, the calculation is:

    level = P + m × (b₁ − b₀)

The defaults are slopes of 1.0, 0.5, and 2.0 price units per bar. Custom
positive, zero, or negative slopes are accepted, provided they are finite
and unique.

## Interpretation and limitations

- This is transparent line arithmetic, not a claim to reproduce every Gann
  angle construction described in George Alexander MacLean's
  *Fibonacci and Gann Applications in Financial Markets*.
- A traditional 1:1 Gann angle depends on chart scaling and the chosen price
  and time units. A slope of 1.0 here means one price unit per bar; it is not
  automatically a visually calibrated 45-degree angle.
- The caller supplies the anchor and bar indices. There is no pivot detection,
  chart-scale calibration, market-data access, signal generation, backtesting,
  or broker integration.
- Outputs can be negative for long horizons or steep negative slopes. They
  are geometric outputs, not validated market prices or trading targets.
- Unit tests cover arithmetic and input validation only. No predictive
  performance is claimed.

Use this helper as an auditable building block for research, not as a
standalone trading system.
