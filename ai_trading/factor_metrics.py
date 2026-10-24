"""Book-aligned alpha-factor quality metrics for EROS."""

from __future__ import annotations

import pandas as pd


def information_coefficient(
    factor: pd.Series,
    forward_returns: pd.Series,
) -> float:
    """Return Spearman rank correlation between factor and forward returns."""
    data = (
        pd.concat([factor, forward_returns], axis=1).apply(pd.to_numeric, errors="coerce").dropna()
    )
    if len(data) < 2:
        return 0.0
    if data.iloc[:, 0].nunique() < 2 or data.iloc[:, 1].nunique() < 2:
        return 0.0
    return float(data.iloc[:, 0].corr(data.iloc[:, 1], method="spearman"))


def daily_information_coefficient(
    data: pd.DataFrame,
    *,
    date_column: str,
    factor_column: str,
    forward_return_column: str,
) -> pd.Series:
    """Return one cross-sectional Spearman IC for each date."""
    required = [date_column, factor_column, forward_return_column]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise KeyError(f"missing required columns: {missing}")

    values = (
        data.groupby(date_column, sort=True, observed=True)
        .apply(
            lambda group: information_coefficient(
                group[factor_column], group[forward_return_column]
            ),
            include_groups=False,
        )
        .rename("information_coefficient")
    )
    return values


def factor_quantile_returns(
    data: pd.DataFrame,
    *,
    factor_column: str,
    forward_return_column: str,
    quantiles: int = 5,
) -> pd.Series:
    """Return mean forward return for each factor quantile."""
    if quantiles < 2:
        raise ValueError("quantiles must be at least 2")
    required = [factor_column, forward_return_column]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise KeyError(f"missing required columns: {missing}")

    values = data[required].apply(pd.to_numeric, errors="coerce").dropna()
    if len(values) < quantiles:
        raise ValueError("not enough observations for the requested quantiles")

    ranks = values[factor_column].rank(method="first")
    labels = pd.qcut(ranks, q=quantiles, labels=False) + 1
    return values.groupby(labels, observed=True)[forward_return_column].mean()


def quantile_turnover(previous: pd.Series, current: pd.Series) -> float:
    """Return the fraction of assets whose quantile membership changed."""
    data = pd.concat([previous.rename("previous"), current.rename("current")], axis=1).dropna()
    if data.empty:
        return 0.0
    return float((data["previous"] != data["current"]).mean())


def factor_rank_autocorrelation(
    previous: pd.Series,
    current: pd.Series,
) -> float:
    """Return Spearman correlation of factor ranks across two periods."""
    data = pd.concat([previous.rename("previous"), current.rename("current")], axis=1)
    return information_coefficient(data["previous"], data["current"])
