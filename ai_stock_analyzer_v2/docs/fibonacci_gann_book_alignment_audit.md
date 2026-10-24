# Fibonacci–Gann Book Alignment Audit

## Purpose and scope

This document is a first-pass alignment audit for the Fibonacci–Gann Research Lab against *Fibonacci and Gann Applications in Financial Markets* by George Alexander MacLean (Wiley, 2005).

It is an engineering gap register, not a claim that every method in the book has been reproduced. The book's chapter contents should be checked directly before any method is described as fully covered. This audit distinguishes what is visible in the current implementation from items that still require source-level review or implementation.

## Current implementation reviewed

Files reviewed on the repository's main branch for this audit:

- `pages/Fibonacci_Gann_Research_Lab.py`
- `modules/fibonacci_gann/signals.py`
- `modules/fibonacci_gann/backtest.py`
- `tests/test_fibonacci_gann_signals.py`
- `docs/fibonacci_gann_research_csv.md`

### Confirmed existing capabilities

- Historical daily OHLC can be uploaded or downloaded through the existing Yahoo Finance/yfinance helper.
- The downloaded CSV starts with placeholder false signals; the downloader does not silently invent trading signals.
- The optional signal rule uses a rolling prior-candle range, excludes the current candle from level calculations, and uses the 38.2% and 61.8% Fibonacci retracement prices plus a Gann 5/8 level.
- The signal is evaluated at the current bar close; the backtester enters no earlier than the next bar's open.
- The backtester supports long-only trades, stop and target exits, position sizing from the current realized equity, per-unit round-trip costs and adverse slippage.
- The backtester documents conservative same-bar stop/target handling, stop-gap risk, and the limitation that drawdown is based on closed-trade equity rather than intratrade mark-to-market.
- Tests cover basic signal generation, lookback exclusion, insufficient history, invalid lookback values, and unordered timestamps.

## Gap register

Status meanings:

- **Present** — the reviewed code clearly implements the stated capability.
- **Partial** — a narrow version exists, but it does not cover the broader topic.
- **Not found in reviewed files** — the listed files do not demonstrate the capability; the wider repository has not yet been exhaustively searched.
- **Requires source verification** — compare the exact method with the book before implementation.

| Topic to audit | Evidence in reviewed code | Status | Next action |
|---|---|---|---|
| Fibonacci retracement levels | Fixed 38.2% and 61.8% levels from the preceding rolling high/low | Partial | Verify level orientation and swing-selection rules against the book; add unit tests for rising and falling ranges |
| Swing-point selection | Uses the highest high and lowest low in a fixed lookback window | Partial | Review whether the book's methods require confirmed pivots, trend context, or manual swing selection |
| Fibonacci extensions / projections | Not used by the current signal generator | Not found in reviewed files | Verify formulas and intended interpretation in the book, then implement separately if appropriate |
| Gann price divisions | Current signal generator uses only the 5/8 level of the prior range | Partial | Audit other divisions and how the book defines the range/origin before adding them |
| Fibonacci fanlines / arcs | No implementation shown in the reviewed files | Not found in reviewed files | Verify the book's construction rules and required chart/time assumptions |
| Fibonacci timelines | No implementation shown in the reviewed files | Not found in reviewed files | Verify anchor selection, units, and interpretation before implementation |
| Combining methods / confirmation | The current entry rule combines a retracement-zone condition with a Gann 5/8 cross | Partial | Document whether the combination matches a specific book method; avoid claiming it does until verified |
| Common calculation and charting errors | OHLC validation and chronology checks exist; broader chart-scale and anchor checks are not demonstrated here | Partial | Create explicit validation cases for missing bars, duplicate dates, bad OHLC, adjusted prices, and ambiguous anchors |
| Backtest timing and risk | Next-bar entry, stop/target logic, equity-aware sizing, costs and slippage are supported | Present for the current research harness | Continue regression tests; document gap risk and closed-trade drawdown limitations in result exports |
| Empirical validity | Tests verify software behavior, not predictive value | Not established | Use out-of-sample and cost-aware tests; do not treat a technically correct implementation as evidence of a trading edge |

## Recommended implementation sequence

1. **Verify the source first.** Review the relevant book chapters and record each method's definition, formula, anchor requirements, and assumptions. Do not infer missing formulas from a technique's name.
2. **Add mathematical tests.** Cover known hand-calculated examples, rising and falling ranges, degenerate ranges, invalid anchors, and boundary conditions.
3. **Implement extensions and projections** only after their exact source-defined formulas and anchor rules are documented.
4. **Implement fanlines, arcs, and timelines** as separate research calculations with explicit anchor/time assumptions. Avoid mixing them into the existing entry rule by default.
5. **Expand Gann levels** only after documenting the range origin and the divisions used by the book.
6. **Compare methods independently and in combinations.** Keep a baseline, use chronological out-of-sample evaluation, include realistic costs/slippage, and report uncertainty.
7. **Expose assumptions in the UI and exported results.** Every signal should be reproducible from the selected method, parameters, source data, and timestamp.

## Acceptance criteria for future feature PRs

- The implementation cites a specific book chapter/section in code or documentation where practical.
- Formulas and anchor conventions are documented, including whether the current candle is excluded.
- Tests use hand-calculated expected values rather than only checking that a result exists.
- Signal generation is causal and has no look-ahead bias.
- Existing backtest timing, cost, slippage, and risk safeguards remain intact.
- The UI clearly labels the feature as research and does not imply profitability.
- Relevant tests, formatting, lint, and CI checks pass before merge.

## Limitations of this audit

This is a first-pass review of the five files listed above, not an exhaustive repository-wide search and not a line-by-line validation of all 11 chapters and appendices. “Not found in reviewed files” must not be interpreted as proof that a capability does not exist elsewhere in the repository. Complete the book-to-repository crosswalk before declaring full coverage.
