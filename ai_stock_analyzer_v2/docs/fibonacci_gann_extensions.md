# Fibonacci extension projection helper

## Source basis and limits

George Alexander MacLean's *Fibonacci and Gann Applications in Financial Markets*
discusses extension levels including 131.8%, 150%, 161.8%, 200%, and 261.8%
(Chapter 2, with later examples in Chapters 5 and 8). The book cautions that
extensions are most useful in price areas without prior trading history and that
other support/resistance evidence matters.

This implementation is a **research helper**, not a complete reproduction of
the book's charting process. It uses a clearly specified three-anchor convention:

- **A — impulse start**
- **B — impulse end**
- **C — pullback end**
- **Projection at ratio r:** `C + (B - A) × r`

The signed impulse supports bullish and bearish projections. Ratios are decimal
multipliers: 1.618 means 161.8% of the A-to-B impulse. Default ratios are
100%, 131.8%, 150%, 161.8%, 200%, and 261.8%.

The inspected book excerpts establish that these levels are discussed, but do
not by themselves establish that this exact three-anchor formula and anchor
selection cover every method described in the book. Confirm the chart/anchor
convention against the relevant figures and text before using this as a
book-faithful implementation.

## Example

For A=100, B=120, C=110, the impulse is +20. The 161.8% projection is
110 + 20 × 1.618 = 142.36. For a downward impulse A=120, B=100, C=110,
the 161.8% projection is 110 + (-20 × 1.618) = 77.64.

## Safety and interpretation

- Anchors are explicit user-selected prices; this helper does not infer swing
  points or automatically create signals.
- It does not connect projections to entries, stops, targets, or broker orders.
- Unit tests establish arithmetic and input validation, not predictive value.
- Extension levels are not guaranteed support/resistance and are not trade advice.
