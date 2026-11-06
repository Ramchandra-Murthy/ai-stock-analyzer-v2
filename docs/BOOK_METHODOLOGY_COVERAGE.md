# Book-to-Repository Methodology Coverage

**Primary reference:** *Hands-On AI Trading with Python, QuantConnect, and AWS* — Jiri Pik, Ernest P. Chan, Jared Broad, Philip Sun and Vivek Singh.  
**Repository reviewed:** `Ramchandra-Murthy/ai-stock-analyzer-v2`  
**Baseline:** `main` at `1e82e344b6e4f38fb915008fcd5e954009b1fd73`  
**Scope:** Documentation-only comparison. This is not a claim that every mapped module reproduces the book's implementation or results.

## How to read this assessment

- **Implemented / related:** A repository capability addresses the same broad problem. It is not necessarily the same algorithm or experiment.
- **Partial:** Some supporting infrastructure exists, but the book's specific method, evaluation or integration is not evident.
- **Gap / not found:** No dedicated implementation was identified in the reviewed `main` tree.
- **Verify:** The concept needs deeper source-level or runtime validation before it can be called complete.

The book is a methodology reference, not a specification to copy wholesale. Examples built around US equities, FX, crypto, QuantConnect or AWS must be adapted to NSE/BSE data, Indian market sessions, security identifiers, costs, liquidity and short-selling constraints.

---

## Executive summary

V2 already has substantial research infrastructure: ML classification, momentum scoring and walk-forward evaluation; regime analysis; mean-reversion and cointegration diagnostics; portfolio optimization; volatility forecasting; execution-cost simulation; risk guards; news sentiment; and fundamental scoring.

The most valuable book-derived gaps are not another general-purpose scanner. They are:

1. A properly evaluated **classifier that selects momentum/trend versus mean-reversion strategies**.
2. **Conditional/corrective risk and allocation policies** with strict out-of-sample controls.
3. **PCA-based statistical-arbitrage research**, clearly distinguished from existing pairs/cointegration tools.
4. **ML-based execution-cost prediction/optimization**, beyond deterministic TWAP/VWAP/POV schedules.
5. **Fundamental clustering** and a comparative study of ranking methods.
6. A controlled **FinBERT-versus-existing-sentiment baseline** experiment.
7. Evidence-grounded LLM/RAG research only after data provenance and evaluation are defined.

Do not start these feature projects until the current integration audit PRs #33–#39 have been reviewed and the live deployment/data path has been verified.

## Part I — Foundations of capital markets and quantitative trading

| Chapter / subject | V2 evidence | Coverage | Follow-up |
|---|---|---|---|
| 1. Market mechanics, participants, data feeds | Shared market-data services, scanners, Data Health page and provider diagnostics | Partial — provider availability and OHLCV checks exist; order-book/microstructure coverage is not established by this review | Audit freshness, timestamp/timezone contracts, corporate actions, spread and liquidity assumptions |
| 1. Brokerages and transaction costs | `algorithmic_trading/trading_costs.py`, `algorithmic_trading/execution.py`, Execution Lab | Related — Indian cost components and simulated execution schedules exist | Verify broker-specific rates, partial fills, impact calibration and effective-date handling |
| 1. Security identifiers and assets | NSE/BSE symbol support, BSE scrip-code support, asset-aware watchlist fields | Partial | Validate symbol changes, delistings, duplicate identifiers and point-in-time universe membership |
| 1. Assets and derivatives | Equity, mutual-fund, crypto, forex and options research areas | Related | Confirm each instrument's market calendar, contract multiplier, expiry and risk conventions |
| 2. Research process and testing | Strategy Lab, Walk-Forward Lab, Strategy Robustness, paper trading and tests | Strong supporting infrastructure | Ensure all strategy reports expose the same reproducible assumptions and benchmark |
| 2. Time and look-ahead bias | `ai_trading/lookahead.py`, `ai_trading/walk_forward.py`, point-in-time utilities | Implemented supporting controls; verify each consumer | Audit all signal-to-fill timing, label availability, corporate-action and universe leakage |
| 2. Parameter sensitivity and optimization | `ai_trading/parameter_sensitivity.py`, `ai_trading/parameter_robustness.py`, walk-forward optimizer | Related | Require stability across parameter neighbourhoods, not just the best parameter cell |
| 2. Margin, diversification and asset selection | Portfolio Optimizer, Advanced Portfolio Lab, options analytics | Partial / related | Validate Indian F&O margin and short-option assumptions; do not infer broker margin from payoff diagrams |
| 2. Indicators and transformations | Feature factory, feature drift, momentum and technical-analysis modules | Related | Add data lineage and point-in-time availability to each feature |

## Part II — Foundations of AI and ML

| Chapter / subject | V2 evidence | Coverage | Follow-up |
|---|---|---|---|
| 3. Problem definition | `ai_trading/ml_model.py`, `ai_trading/ml_scanner.py`, configurable horizon and threshold | Partial | Define a model registry: target, horizon, label rule, universe, rebalance, costs, benchmark and intended use |
| 4. Data collection and EDA | Market-data services, Data Health, scanner diagnostics | Partial | Add point-in-time dataset snapshots and reproducible data-quality reports |
| 4. Preprocessing and feature selection | `ai_trading/features.py`, `ai_trading/feature_factory.py`, `ai_trading/feature_drift.py` | Related | Verify preprocessing is fitted only on training data and persisted with model version |
| 4. Time-series dataset splits | Purged walk-forward and chronological validation modules | Strong supporting infrastructure | Test purge/embargo boundaries for each label horizon and multi-symbol panel |
| 5. Classification | `ai_trading/ml_model.py`, `ai_trading/ml_scanner.py`, calibration and diagnostics | Implemented | Compare models using calibrated probabilities, class balance and net-of-cost utility |
| 5. Ranking | `ai_trading/momentum_scoring.py`, momentum validation and walk-forward modules | Implemented / related | Compare cross-sectional ranking objectives against classification and absolute-return prediction |
| 5. Clustering | Fundamental snapshots and quality scoring exist in `ai_trading/fundamental_intelligence.py` | Partial — normalization/scoring is not clustering | Evaluate clustering only if it adds stable, interpretable group structure |
| 5. Language models | News schema and sentiment pipeline exist | Partial — structured news and baseline sentiment are not evidence of an LLM/RAG pipeline | Build source-linked retrieval/summarization only with provenance and factuality tests |

## Part III — Chapter 6: Applied ML examples

The book's Chapter 6 contains 19 examples. The mapping below deliberately distinguishes related V2 components from an implementation of the book's specific method.

| # | Book example | V2 evidence | Status / recommended action |
|---:|---|---|---|
| 1 | ML trend scanning with MLFinLab | ML scanner, trend features, momentum scoring and walk-forward evaluation | **Partial.** Similar research objective; no claim of MLFinLab trend-scanning equivalence. Compare labels and event horizons before adopting |
| 2 | Factor preprocessing for regime detection | Regime engines, regime context and feature factory | **Partial.** Regime tooling exists; verify factor preprocessing, normalization and point-in-time behaviour |
| 3 | Reversion vs. trending: strategy selection by classification | ML classifier, regime context, mean-reversion and momentum/trend strategies | **Gap — high priority.** No dedicated classifier choosing between strategy families was identified |
| 4 | Alpha by Hidden Markov Models | Several deterministic/probabilistic regime and transition diagnostics | **Gap / verify.** No dedicated HMM implementation was identified in the reviewed tree |
| 5 | FX SVM wavelet forecasting | Forex Lab and sequence/ML modules | **Gap / low priority for NSE equity focus.** No dedicated SVM-wavelet pipeline identified |
| 6 | Dividend harvesting / high-yield asset selection | Fundamental intelligence and equity research | **Gap / verify.** No dedicated dividend-harvesting strategy with ex-date, payout and total-return treatment identified |
| 7 | Effect of positive-negative splits | Corporate-action research would be needed | **Gap.** No dedicated split-event study identified |
| 8 | Stop loss based on historical volatility and drawdown recovery | Risk Guards Lab, volatility forecasts, drawdown diagnostics | **Partial.** Existing close-based guards are not the book's adaptive historical-volatility/drawdown-recovery method; gap and intraday fill limitations must remain explicit |
| 9 | ML trading-pairs selection | `ai_trading/cointegration.py`, Pairs Research and mean-reversion diagnostics | **Partial.** Cointegration/pairs research exists; ML selection of candidate pairs is not established |
| 10 | Stock selection through clustering fundamental data | `ai_trading/fundamental_intelligence.py` | **Gap — medium priority.** Fundamentals are normalized and scored; no dedicated clustering workflow identified |
| 11 | Inverse-volatility rank and allocate to futures | Portfolio Optimizer and inverse-volatility allocation | **Partial / related.** Portfolio allocation exists; futures-universe ranking, roll and contract-specific treatment require separate validation |
| 12 | Trading-cost optimization | Execution Lab, TWAP/VWAP/POV schedules, square-root impact and transaction-cost sensitivity | **Partial.** Deterministic cost simulation exists; ML cost prediction or optimizer from observed execution data is not established |
| 13 | PCA statistical-arbitrage mean reversion | Cointegration and pairs research | **Gap — medium priority.** PCA residual construction is distinct from pairwise cointegration; build only with robust out-of-sample testing |
| 14 | Temporal CNN prediction | Sequence model and ML prediction modules | **Partial / verify.** A sequence model exists; do not call it a temporal CNN unless architecture inspection confirms it |
| 15 | Gaussian classifier for direction prediction | Classification model and ML Signal Lab | **Gap / low priority.** No dedicated Gaussian classifier identified; treat as a benchmark, not an assumed upgrade |
| 16 | LLM summarization of Tiingo news | News schema, news service and sentiment pages | **Partial.** News ingestion/sentiment exists; no evidence here of source-grounded LLM summarization |
| 17 | Head-and-shoulders pattern matching with CNN | Technical scanners and pattern research | **Gap / low priority.** No dedicated CNN pattern-matching model identified |
| 18 | Amazon Chronos model | Forecasting and volatility forecast modules | **Gap / research only.** No Chronos integration identified; benchmark against simple baselines before considering deployment |
| 19 | FinBERT model | TF-IDF/logistic-regression sentiment baseline in `ai_trading/financial_sentiment_model.py` | **Gap — medium priority.** FinBERT is a candidate comparison, not automatically superior; compare on identical time-aware labelled data |

## Chapter 7 — Reinforcement learning for hedging

**Book method:** A reinforcement-learning workflow for options hedging, including training in a simulated environment and evaluation/refinement with market data.

**V2 evidence:** Options analytics, options backtesting and paper-trading modules are present. No dedicated reinforcement-learning hedging agent or training environment was identified in the reviewed `main` tree.

**Assessment:** Gap / advanced research. Do not prioritize until the options data, payoff, transaction-cost, margin and paper-trading assumptions are verified. Any RL result must be compared with a simple delta-hedging baseline and evaluated on unseen market periods.

## Chapter 8 — Corrective AI and Conditional Parameter Optimization

**Book method:** Use corrective AI to adjust an existing decision process and condition parameter/portfolio optimization on market context rather than relying on one unconditional optimum.

**V2 evidence:** Adaptive engine, adaptive performance, learning loop, regime context/decision, parameter sensitivity and walk-forward modules.

**Assessment:** Partial / related. V2 has adaptive components, but their existence does not establish the book's corrective-AI or CPO methodology. The next audit should trace exactly how adjustments are learned, bounded, selected and evaluated out of sample.

**Recommended experiment:** Compare (a) fixed baseline, (b) unconditional optimized parameters and (c) regime-conditional parameters using identical walk-forward folds, turnover and Indian transaction costs. Keep a final untouched holdout.

## Chapter 9 — LLMs and generative AI

**Book method:** LLM selection, prompt engineering, retrieval-augmented question answering, summarization and platform/cost considerations.

**V2 evidence:** Structured news records, news services and baseline sentiment analysis. No dedicated retrieval-augmented generation or evidence-grounded LLM application was identified in the reviewed tree.

**Assessment:** Partial / gap. A research assistant could be useful, but only if every answer links to source documents and dates, distinguishes facts from interpretation, and refuses unsupported claims. Do not connect generated text directly to trade execution.

---

## India-specific adaptation checklist

Before porting a book example, verify:

- NSE/BSE symbol mapping, corporate actions, delisted names and survivorship-free point-in-time universes.
- Exchange trading sessions, holidays, auction periods, price bands and intraday timestamp semantics.
- Indian brokerage, STT, GST, stamp duty, exchange and SEBI charges, plus broker-specific charges and effective dates.
- Liquidity, bid-ask spread, market impact, partial fills and circuit-limit behaviour.
- F&O lot sizes, expiry calendars, contract multipliers, margin and short-option constraints.
- Whether the data source actually provides the required historical fields at the required frequency.
- Whether the strategy is executable for the intended Indian account type and instrument.

## Recommended PR sequence

| Sequence | Proposed PR | Why / acceptance criteria |
|---:|---|---|
| 0 | Complete integration audit PRs #33–#39 | Do not layer research on top of unresolved data, execution, queue or persistence defects |
| 1 | Research: momentum vs. mean-reversion strategy selector | Purged walk-forward comparison against always-momentum, always-reversion and regime-rule baselines; include costs, turnover, calibration and per-regime results |
| 2 | Research: adaptive volatility/drawdown stop policy | Compare fixed, trailing and adaptive rules; include gaps, next-bar execution assumptions, costs and drawdown-recovery analysis |
| 3 | Research: conditional parameter optimization | Compare fixed vs. unconditional vs. conditional parameter selection on identical folds; limit search and report multiple-testing risk |
| 4 | Research: ML execution-cost prediction | Use timestamped execution/market observations; chronological holdout; compare with current deterministic impact and TWAP/VWAP/POV baselines |
| 5 | Research: PCA statistical arbitrage | Point-in-time universe; fit PCA only on training data; residual stationarity diagnostics; realistic Indian shorting/hedging constraints and net costs |
| 6 | Research: fundamental clustering | Point-in-time fundamentals; missingness and scaling fitted on training data; cluster stability and forward-return utility |
| 7 | Research: FinBERT benchmark | Same human-labelled, time-split news set as TF-IDF baseline; macro-F1, calibration, latency and cost; no trading integration until it wins out of sample |
| 8 | Research: evidence-grounded news RAG | Source/date provenance, citation coverage, factuality tests, prompt-injection resistance and cost/latency reporting |
| Later | Chronos and RL options hedging experiments | Only after simpler baselines, data contracts and paper-trading assumptions are stable |

## Non-negotiable research acceptance criteria

Every new predictive or adaptive method must:

1. Define its target, prediction horizon, universe and decision timestamp before training.
2. Use chronological splits with purging/embargo where labels overlap.
3. Fit preprocessing, feature selection and model tuning only on training data.
4. Compare with simple, relevant baselines.
5. Include Indian transaction costs, turnover, slippage and realistic entry/exit timing.
6. Report calibration and uncertainty where probabilities are shown.
7. Report performance by symbol, sector and market regime where sample sizes permit.
8. Include parameter/model stability and multiple-testing considerations.
9. Preserve reproducible seeds, data windows, feature definitions and model versions.
10. Remain research-only until independently reviewed and paper-trading evidence supports promotion.

## Source and evidence notes

- Chapter names and all 19 Chapter 6 example titles were transcribed from the uploaded EPUB's Table of Contents.
- Repository mapping was made against the public `main` tree and README/roadmap at the baseline commit listed above.
- A path match or README feature description establishes that a capability exists in the repository, not that it reproduces the book's exact algorithm or has passed independent validation.
- Items marked "not identified" mean no dedicated implementation was found in this review; they are not proof that no experimental code exists on any non-main branch.
