"""Book-aligned stability diagnostics for walk-forward results."""

from __future__ import annotations

import pandas as pd

from ai_trading.risk_metrics import max_drawdown, sharpe_ratio


def walk_forward_window_metrics(
    returns: pd.Series,
    *,
    window_size: int,
    periods_per_year: float = 252.0,
) -> pd.DataFrame:
    """Summarize return and risk metrics for consecutive walk-forward windows."""
    if window_size < 2:
        raise ValueError("window_size must be at least 2")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")

    clean = pd.to_numeric(returns, errors="coerce").dropna().reset_index(drop=True)
    if len(clean) < window_size:
        raise ValueError("not enough observations for the requested window size")

    rows: list[dict[str, float | int]] = []
    for window_number, start in enumerate(range(0, len(clean) - window_size + 1, window_size), 1):
        window = clean.iloc[start : start + window_size]
        wins = int((window > 0.0).sum())
        rows.append(
            {
                "window": window_number,
                "start": start,
                "end": start + window_size - 1,
                "total_return": float((1.0 + window).prod() - 1.0),
                "win_rate": float(wins / len(window)),
                "sharpe_ratio": sharpe_ratio(window, periods_per_year=periods_per_year),
                "max_drawdown": max_drawdown(window),
            }
        )

    return pd.DataFrame(rows)


def stability_summary(window_metrics: pd.DataFrame) -> dict[str, float | None]:
    """Return dispersion diagnostics across walk-forward windows."""
    required = {"total_return", "win_rate", "sharpe_ratio", "max_drawdown"}
    missing = sorted(required.difference(window_metrics.columns))
    if missing:
        raise KeyError(f"missing required columns: {missing}")
    if window_metrics.empty:
        return {
            "windows": 0.0,
            "return_mean": None,
            "return_std": None,
            "win_rate_mean": None,
            "sharpe_mean": None,
            "max_drawdown_worst": None,
        }

    return {
        "windows": float(len(window_metrics)),
        "return_mean": float(window_metrics["total_return"].mean()),
        "return_std": (
            float(window_metrics["total_return"].std(ddof=1)) if len(window_metrics) > 1 else 0.0
        ),
        "win_rate_mean": float(window_metrics["win_rate"].mean()),
        "sharpe_mean": float(window_metrics["sharpe_ratio"].mean()),
        "max_drawdown_worst": float(window_metrics["max_drawdown"].max()),
    }
