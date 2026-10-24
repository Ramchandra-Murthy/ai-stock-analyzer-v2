# Fibonacci-Gann Research Lab: historical CSV helper

This utility creates a CSV in the format accepted by `pages/Fibonacci_Gann_Research_Lab.py`.

## 1. Install dependencies

The repository already declares `yfinance` and `pandas`. In the project environment, run:

```bash
uv sync
```

Or in a separate Python environment:

```bash
python -m pip install yfinance pandas
```

## 2. Download around five years of daily history

From the repository root:

```bash
python scripts/make_research_csv.py --symbol ^NSEI --start 2021-01-01 --output NIFTY50_research.csv
```

For Reliance:

```bash
python scripts/make_research_csv.py --symbol RELIANCE.NS --start 2021-01-01 --output RELIANCE_research.csv
```

An optional `--end YYYY-MM-DD` is supported; the end date is exclusive. The output has these columns:

```text
timestamp,open,high,low,close,signal
```

Upload the resulting CSV to the Research Lab.

## Critical signal limitation

The script downloads daily OHLC prices only. It sets `signal` to `false` for every row as a safe placeholder; it does **not** calculate Fibonacci-Gann buy signals. Populate the signal column using a documented strategy before interpreting any backtest. A signal must be knowable at that bar's close; the Research Lab enters no earlier than the next bar open.

The included `data/fibonacci_gann_csv_template.csv` has fabricated example prices to demonstrate the schema; do not use those rows as market history.

## Data-source limitations

`yfinance` is an unofficial Yahoo Finance interface, not an exchange-certified feed. Downloads may be unavailable, rate-limited, delayed, or revised. Check the downloaded dates and prices against a trusted source. This is a research-only workflow: it does not fetch live quotes or place broker orders.
