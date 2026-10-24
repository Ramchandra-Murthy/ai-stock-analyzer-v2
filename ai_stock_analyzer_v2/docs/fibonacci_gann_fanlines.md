# Fibonacci fanline calculation helper

## Source basis

George Alexander MacLean's *Fibonacci and Gann Applications in Financial Markets*,
Chapter 3 (pp. 30–32 in the uploaded edition), describes a fanline as follows:
use the origin and the significant extreme of a price move; plot commonly used
38.2%, 50%, and 61.8% retracement points on the vertical side of the move's
right-triangle construction; draw lines from the origin through those points;
then extend the lines over time. The book describes the lines as speedlines and
notes that their values rise over time for a low-to-high move and fall over time
for a high-to-low move.

## Implementation

The caller supplies the origin price, extreme price, elapsed-bar distance from
origin to extreme, and elapsed bars at which to evaluate the fanlines. For each
ratio r, the point on the extreme-time vertical is:

    extreme_price - (extreme_price - origin_price) × r

The line is drawn from the origin through that point and extended linearly in
time. Defaults are 38.2%, 50%, and 61.8%. No pivot detection, chart scaling,
market-data access, signal generation, backtesting, or broker actions are included.

## Important limitations

- Bar count is used as the time axis. The result can differ from a chart that
  uses calendar time, trading-session gaps, or a price/time scale calibrated to
  a particular market.
- The book warns that fanlines can be distorted by the chart's parameters and
  screen scale, and that very steep or long-running fans may be less useful.
- A line break is a possible focus toward the next fanline, not a guaranteed
  price target or direction forecast. The book emphasizes using traditional
  analysis and other evidence for confirmation.
- Unit tests verify the specified geometry and validation only; they do not
  establish predictive value.

This helper is an auditable research implementation of the described geometry,
not a claim that software-generated fanlines remove the construction and
interpretation issues discussed in the book.
