"""Book-aligned parameter sensitivity diagnostics for backtest returns."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from ai_trading.risk_metrics import max_drawdown, sharpe_ratio


def parameter_sensitivity_report(
    returns_by_parameter: Mapping[str, pd.Series],
    *,
    periods_per_year: float = 252.0,
) -> pd.DataFrame:
    """Compare return and risk metrics across parameter configurations."""
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    if not returns_by_parameter:
        raise ValueError("returns_by_parameter must not be empty")

    rows: list[dict[str, float | str]] = []
    for parameter, returns in returns_by_parameter.items():
        clean = pd.to_numeric(returns, errors="coerce").dropna().reset_index(drop=True)
        if clean.empty:
            raise ValueError(f"returns for {parameter!r} must contain valid observations")

        rows.append(
            {
                "parameter": str(parameter),
                "observations": float(len(clean)),
                "total_return": float((1.0 + clean).prod() - 1.0),
                "sharpe_ratio": sharpe_ratio(clean, periods_per_year=periods_per_year),
                "max_drawdown": max_drawdown(clean),
            }
        )

    result = pd.DataFrame(rows)
    result["return_rank"] = result["total_return"].rank(ascending=False, method="min")
    result["sharpe_rank"] = result["sharpe_ratio"].rank(ascending=False, method="min")
    return result.sort_values("return_rank").reset_index(drop=True)


def parameter_sensitivity_summary(
    report: pd.DataFrame,
) -> dict[str, float | str | None]:
    """Summarize the performance spread across parameter configurations."""
    required = {"parameter", "total_return", "sharpe_ratio", "max_drawdown"}
    missing = sorted(required.difference(report.columns))
    if missing:
        raise KeyError(f"missing required columns: {missing}")
    if report.empty:
        return {
            "configurations": 0.0,
            "best_parameter": None,
            "worst_parameter": None,
            "return_spread": None,
            "sharpe_spread": None,
            "drawdown_spread": None,
        }

    best = report.loc[report["total_return"].idxmax()]
    worst = report.loc[report["total_return"].idxmin()]

    return {
        "configurations": float(len(report)),
        "best_parameter": str(best["parameter"]),
        "worst_parameter": str(worst["parameter"]),
        "return_spread": float(report["total_return"].max() - report["total_return"].min()),
        "sharpe_spread": float(report["sharpe_ratio"].max() - report["sharpe_ratio"].min()),
        "drawdown_spread": float(report["max_drawdown"].max() - report["max_drawdown"].min()),
    }
