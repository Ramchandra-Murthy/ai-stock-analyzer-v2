# AI Institutional Equity Research Platform (AI_STOCK_ANALYZER)

Equity research and valuation platform for Indian and global stocks, built with Python 3.13. It combines market data, technical and fundamental scoring, sum-of-the-parts (SOTP) valuation, forecasting, scanners, paper trading and PDF research reports, behind a Streamlit UI, a FastAPI service and a CLI.

> **Disclaimer.** For research and educational use only. Scores, target prices and signals are model outputs built on third-party data that may be delayed or incomplete. Nothing here is investment advice or a recommendation to buy or sell any security.

## Quick start

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/). `pyproject.toml` and `uv.lock` are the source of truth for dependencies; CI and the Docker image use them.

```bash
uv sync --locked              # install locked dependencies
make doctor                   # check which data providers work from this machine
make run-web                  # Streamlit UI  -> app.py (the full integrated app)
make run-api                  # FastAPI       -> api.main:app
make run-cli                  # CLI           -> main.py --ticker AAPL
```

Without `make`, run the underlying commands directly, for example `uv run streamlit run app.py`. The sidebar groups every page (market, research, algorithmic and AI trading, options).

Run `make doctor` first. Whether option chains and BSE data work depends on your network and credentials, and it prints PASS/WARN/FAIL for each provider with the next step (credential values are never printed).

### Research pages added in this version

All are research tools: historical results, not forecasts; no page places orders.

| Page | What it does |
| --- | --- |
| Strategy Lab | Supertrend, Donchian, z-score, RSI(2) and ensemble backtests with real NSE costs, volatility targeting and an optional market-regime filter |
| Walk-Forward Lab | Re-tunes parameters in rolling windows using only past data, reports stitched out-of-sample results and a parameter-stability heatmap |
| Momentum Portfolio | Top-N momentum, equal or inverse-volatility weights, monthly rebalance, costs on actual turnover, vs an equal-weight benchmark |
| Risk Dashboard | Historical VaR/CVaR, correlation, risk contribution, drawdown and a circuit-breaker simulation |
| Options Strategy Builder | Straddles, strangles, spreads and iron condor: exact payoff, breakevens, Greeks, IV rank (no margin calculation) |
| Pairs Research | Engle-Granger cointegration scan and an out-of-sample spread backtest (shorting limits apply in India) |
| Strategy Robustness | Block-bootstrap ranges for Sharpe/CAGR/drawdown and a deflated Sharpe ratio that discounts the best of many tried parameter sets |
| Portfolio Optimizer | Min-variance, max-Sharpe, risk-parity and hierarchical risk parity weights tested walk-forward against equal weight, plus risk-based and fractional-Kelly position sizing |
| ML Signal Lab | Logistic-regression / gradient-boosting direction signals with purged walk-forward training (no label leakage), shown against the always-up base rate |
| Volatility Forecast | EWMA and GARCH(1,1) volatility forecasts, decay path and an out-of-sample QLIKE scoreboard |
| Sector Rotation | Relative-strength quadrants of NSE sector indices vs NIFTY 50 |
| Alerts | Telegram / e-mail status and test; `scripts/run_alerts.py` sends signal-change and drawdown alerts from cron |

NSE cost presets (STT, stamp duty, exchange, SEBI, GST) are in `algorithmic_trading/trading_costs.py` and were checked against NSE and a broker rate card on the date shown in `RATES_VERIFIED`; re-check them and your broker's brokerage. The NIFTY lot size default (65) comes from broker notes and NSE changes it by circular, so verify it. See [docs/ROADMAP.md](docs/ROADMAP.md) for what to build next.

Copy `.env.example` to `.env` and add your Dhan credentials to enable live option chains; the app loads `.env` automatically at startup. Without credentials the options pages fall back to NSE and Yahoo Finance, which often cannot serve Indian index option chains from cloud or restricted networks.

### Docker

```bash
docker build -t ai-stock-analyzer .
docker run -p 8501:8501 ai-stock-analyzer
```

The container serves the integrated app on port 8501 and runs as an unprivileged user. Pass credentials at run time (`docker run --env-file .env ...`); `.env` is deliberately excluded from the image. SQLite files live inside the container unless you mount a volume.

### Streamlit Community Cloud

1. Push this repository to your own GitHub account (see below).
2. At [share.streamlit.io](https://share.streamlit.io) choose **Create app**, pick the repository and branch `main`, and set the main file path to `app.py`.
3. Under **Advanced settings** select **Python 3.13** and paste your secrets in TOML form, for example:

   ```toml
   DHAN_CLIENT_ID = "your-client-id"
   DHAN_ACCESS_TOKEN = "your-access-token"
   ```

Community Cloud installs from `uv.lock` (it takes priority over `requirements.txt` and `pyproject.toml`), which already pins everything the app needs. Cloud IP addresses are often blocked by NSE and Yahoo, so live option chains need the Dhan credentials above. Files written to disk (the SQLite databases) do not survive an app restart there.

### Putting this on GitHub

This is a standalone repository with its own history and no remote. Create an empty repository on GitHub, then:

```bash
git remote add origin https://github.com/<you>/<new-repo>.git
git push -u origin main
```

## Configuration

Secrets are read from environment variables (or Streamlit secrets where noted). Never commit them: `.env` and `.streamlit/secrets.toml` are git-ignored.

| Variable | Used for |
| --- | --- |
| `DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN` | Dhan live market data (env or Streamlit secrets) |
| `DHAN_SECURITY_MAP_JSON` | Optional map of `"NSE:SYMBOL"` / `"BSE:SCRIPCODE"` to Dhan security IDs for live equity candles (see `.env.example`) |
| `SUPABASE_URL`, `SUPABASE_SECRET_KEY` (or `SUPABASE_SERVICE_ROLE_KEY`) | Optional durable watchlist storage |
| `WATCHLIST_DATABASE_PATH` | Local SQLite path for the watchlist |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_EMAIL_TO` | Optional alert channels (never displayed or logged) |
| `ALERT_SYMBOLS`, `ALERT_STRATEGY`, `ALERT_DRAWDOWN` | What `scripts/run_alerts.py` watches |
| `EROS_SCAN_DB` | SQLite path for scan history (default `data/eros_scans.sqlite3`) |

SQLite databases are created on first run and are not tracked in git.

## Performance notes

Streamlit re-runs a page on every click, so the app avoids repeating slow network calls:

- `services/cached_download.py` reuses Yahoo downloads for 15 minutes (60 seconds for 5-day price pulls). It is size-bounded, never caches errors, and caches empty results for only 5 seconds so a provider hiccup recovers quickly.
- Option chains are reused for 15 seconds (5 seconds for failures); see `fetch_option_chain_cached`.
- Backtests compound each trade's returns with one vectorised grouped product, about 40% faster than before with identical results.

Caches live in memory, so restarting the app clears them. Most of the remaining wait in a real session is the market-data network, not CPU.

## Development

```bash
make test         # pytest tests/
make lint         # ruff + black (check only)
make format       # ruff --fix + black
make typecheck    # mypy on the currently type-clean surface
make clean        # remove caches
```

Continuous integration (`.github/workflows/`) runs Ruff, Black, a mypy check on a curated set of services, a focused pytest selection, a Docker build and a container health check. A separate non-blocking job runs the entire `tests/` directory.

## Project layout

| Path | Contents |
| --- | --- |
| `app.py`, `pages/`, `modules/`, `components/` | Integrated Streamlit app (`interfaces/streamlit/` is a smaller legacy entry point) |
| `api/` | FastAPI service and scan manager |
| `core/`, `domain/` | Value objects, typed primitives (`Decimal`-based money and percentages), serialization |
| `services/`, `engine/` | Scoring, valuation, SOTP, recommendations, market-data providers |
| `forecast/`, `application/forecast/` | Forecast engine |
| `scanner/`, `strategy/`, `algorithmic_trading/`, `ai/`, `ai_trading/` | Scanners, strategies, paper trading and ML signals |
| `reports/` | PDF research report generation |
| `tests/` | Test suite |

## Engineering standards

- Strict typing is the goal. mypy currently gates a curated set of modules; widening it is ongoing work.
- Financial value objects in `core/` use `decimal.Decimal`. Much of the analytics layer still uses `float`; migrating monetary calculations is a tracked improvement area.
- Ruff (including undefined-name and redefinition checks) and Black are enforced in CI.

## License

MIT. See [LICENSE](LICENSE). Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
