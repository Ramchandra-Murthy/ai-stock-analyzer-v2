# Roadmap: algorithms and improvements

Everything here is research tooling. None of it should place live orders without a separate,
deliberate, tested execution layer, and no backtest result is a promise of future returns.

## Already in the repo

| Area | Where |
| --- | --- |
| Trend, breakout, mean reversion, momentum ranking, ensemble vote, volatility targeting | `algorithmic_trading/advanced_strategies.py`, tested for no look-ahead |
| Strategy backtests on any NSE/BSE stock | `pages/Strategy_Lab.py` (`algorithmic_trading/strategy_lab.py`) |
| Walk-forward validation, costs, position sizing, risk | `walk_forward_validation.py`, `trading_costs.py`, `position_sizing.py`, `portfolio_risk.py` |
| Options: provider chains, IV, Greeks, V2 paper trading | `services/options_analytics.py`, `engine/nifty_options_*.py` |

## Highest value next (in this order)

1. **Walk-forward the Strategy Lab.** Optimise parameters on a rolling in-sample window and
   report only out-of-sample results. This is the single biggest guard against fooling yourself,
   and `walk_forward_validation.py` already provides the pieces. Add a "parameter stability"
   heatmap: a good strategy works across a neighbourhood of settings, not one lucky cell.
2. **Multi-stock portfolio backtest.** `top_momentum_weights` and `volatility_target_scale`
   exist but are not yet exposed. Add a page that ranks an index universe by momentum, holds the
   top N with volatility-scaled weights, rebalances monthly, and charges realistic Indian costs.
   `trading_costs.py` has fields for brokerage, STT, exchange charges, stamp duty and GST, but
   every rate defaults to zero (GST 18%): fill in your broker's real rates first. The Strategy
   Lab currently uses a flat basis-point cost instead.
3. **Regime filter.** Gate trend strategies on a market regime (index above its 200-day average,
   India VIX level) and mean-reversion strategies on the opposite. `regime_engine.py` is the
   natural home.
4. **Options strategy analytics.** Payoff diagrams and Greeks for iron condor, straddle/strangle,
   bull/bear spreads and calendar spreads from the live chain, plus an IV-percentile and
   IV-rank gauge so premium-selling is only suggested when IV is rich. Analytics only; no orders.
5. **Pairs / statistical arbitrage** between cointegrated NSE pairs (for example private-sector
   banks), using an Engle-Granger test and a z-score on the spread. Needs futures or intraday
   shorting to be tradable in India, so keep it as research until that is decided.
6. **Risk overlays.** Portfolio-level drawdown circuit breaker, correlation-aware position caps,
   and CVaR reporting next to volatility.

## Engineering improvements

- Cache the remaining market downloads. `services/cached_download.py` now covers six pages and
  the options path; `modules/intraday.py` and the scanners use their own caches. Fetching the
  16 live-board batches in parallel could cut that page's wait several-fold, but Yahoo rate-limits
  parallel calls, so measure it against the real provider before changing it.
- Replace the roughly 229 `float(` calls in `services/` with `Decimal` or integer
  paise, starting with anything that produces a target price or position size.
- Narrow the 114 `except Exception` blocks and replace `print` with `logging`.
- Widen the mypy gate beyond the 8 curated service files, fixing errors in batches.
- ~~Add the investment-advice disclaimer to every page under `pages/`.~~ Done: `components/disclaimer.py`,
  enforced by `tests/test_page_disclaimers.py`, which fails if a page has none.
- Split files over 1,000 lines (`modules/intraday.py`, the SOTP evidence service).

## What not to add

- Anything that claims a fixed win rate or "guaranteed" signal.
- Machine-learning price prediction without walk-forward, purged cross-validation and a
  benchmark it must beat after costs. Most such models only fit noise.
- Live order placement before paper trading has run for months and a kill switch exists.

## Done in the latest iteration

Walk-forward optimisation, regime filter, momentum portfolio, risk dashboard, options strategy
builder, pairs research, alerts and NSE cost presets are implemented and unit-tested.

Since then: BSE-aware research pages and a Data Health page, minimum-CVaR and rebalance planning,
efficient frontier, Black-Litterman, Cornish-Fisher VaR, Monte Carlo and stress tests, and a
sector and risk concentration report (all in the Advanced Portfolio Lab).

## Still open

- Sector classification beyond the 80-stock curated list (`scanner/sectors.py`); a live source
  such as the exchange's industry file would replace the hand-assigned map.

- Launch the app against live data and fix whatever real providers surface (not done offline).
- Survivorship-free universes for the momentum page (it uses today's large-cap list).
- Live option-chain premiums inside the strategy builder (it prices with Black-Scholes).
- Futures-based pairs execution modelling; margin calculation for short options.
- Merge upstream GitHub changes (main has moved since this branch was cut).
