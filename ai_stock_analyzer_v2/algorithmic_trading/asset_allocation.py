"""Asset-allocation utilities for NSE/BSE portfolio research.

Adapted from the allocation concepts covered in Chapter 9 of Laurent Bernut's
*Algorithmic Short Selling with Python, Second Edition*. These functions
provide transparent allocation baselines rather than declaring one method
universally optimal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from algorithmic_trading.portfolio_risk import dynamic_risk_appetite


def equal_weight(returns: pd.DataFrame) -> pd.Series:
    """Allocate equally across assets with available return history."""
    if returns.empty:
        return pd.Series(dtype=float)
    columns = list(returns.columns)
    return pd.Series(1.0 / len(columns), index=columns, dtype=float)


def inverse_volatility_weight(
    returns: pd.DataFrame,
    annualization: int = 252,
) -> pd.Series:
    """Allocate inversely to realized annualized volatility."""
    if returns.empty:
        return pd.Series(dtype=float)
    if annualization <= 0:
        raise ValueError("annualization must be greater than zero")

    volatility = returns.std(ddof=1) * np.sqrt(annualization)
    volatility = volatility.replace([np.inf, -np.inf], np.nan)

    # A zero-volatility series should receive the strongest inverse-volatility
    # weight, not be discarded as a missing value.
    zero_volatility = volatility.eq(0)
    if zero_volatility.any():
        count = int(zero_volatility.sum())
        return pd.Series(
            np.where(zero_volatility, 1.0 / count, 0.0),
            index=returns.columns,
            dtype=float,
        )

    inverse = volatility.rdiv(1.0)
    inverse = inverse.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    total = float(inverse.sum())
    if total <= 0:
        return equal_weight(returns)
    return inverse / total


def minimum_variance_weight(
    returns: pd.DataFrame,
    ridge: float = 1e-8,
) -> pd.Series:
    """Estimate long-only minimum-variance weights with a covariance solve."""
    if returns.empty:
        return pd.Series(dtype=float)
    if ridge < 0:
        raise ValueError("ridge must be non-negative")

    columns = list(returns.columns)
    covariance = returns.cov().to_numpy(dtype=float)
    covariance = np.nan_to_num(covariance, nan=0.0)
    covariance += np.eye(len(columns)) * ridge

    try:
        inverse_covariance = np.linalg.pinv(covariance)
        raw = inverse_covariance @ np.ones(len(columns))
    except np.linalg.LinAlgError:
        return equal_weight(returns)

    raw = np.clip(raw, 0.0, None)
    total = float(raw.sum())
    if total <= 0 or not np.isfinite(total):
        return equal_weight(returns)
    return pd.Series(raw / total, index=columns)


def apply_weight_cap(weights: pd.Series, maximum: float) -> pd.Series:
    """Apply a hard per-asset cap, leaving any unallocatable amount in cash.

    When the cap permits full investment, excess weight from capped assets is
    redistributed proportionally across uncapped assets. If the cap makes full
    investment impossible (for example, four assets capped at 20%), the result
    deliberately sums to less than one rather than violating the cap.
    """
    if maximum <= 0 or maximum > 1:
        raise ValueError("maximum must be between 0 and 1")

    positive = weights.clip(lower=0.0).fillna(0.0)
    total = float(positive.sum())
    if total <= 0 or positive.empty:
        return positive

    base = positive / total
    result = pd.Series(0.0, index=weights.index, dtype=float)
    active = base[base > 0].copy()
    remaining = 1.0

    while not active.empty and remaining > 1e-12:
        proposed = active / float(active.sum()) * remaining
        capped = proposed[proposed > maximum + 1e-12]
        if capped.empty:
            result.loc[proposed.index] = proposed
            break

        capped_symbols = capped.index
        result.loc[capped_symbols] = maximum
        remaining -= maximum * len(capped_symbols)
        active = active.drop(index=capped_symbols)

    return result.clip(lower=0.0, upper=maximum)


def allocation_summary(weights: pd.Series) -> pd.DataFrame:
    """Return an auditable allocation table."""
    return pd.DataFrame(
        {
            "weight": weights,
            "weight_pct": weights * 100.0,
        }
    )


def upper_band_limit(
    st_dd: float,
    lt_dd: float,
    corr_adj: float,
    lt_dd_tolerance: float,
    st_dd_tolerance: float,
    lqdty_haircut: float,
) -> float:
    """Calculate the hard allocation band from strategy failure geometry."""
    if st_dd <= 0 or lt_dd <= 0:
        raise ValueError("drawdowns must be positive")
    if lt_dd_tolerance <= 0 or st_dd_tolerance <= 0:
        raise ValueError("drawdown tolerances must be positive")
    if not 0 <= corr_adj <= 1 or not 0 <= lqdty_haircut <= 1:
        raise ValueError("correlation and liquidity adjustments must be in [0, 1]")

    min_dd = min(st_dd_tolerance / st_dd, lt_dd_tolerance / lt_dd)
    return round(
        min(min_dd * (1 - corr_adj), 1) * (1 - lqdty_haircut),
        2,
    )


def risk_appetite(
    equity_curve: pd.Series | np.ndarray | list[float],
    max_drawdown_tolerance: float,
    min_risk: float,
    max_risk: float,
    smoothing_span: int = 20,
    curve_shape: str = "linear",
    drawdown_window: int = 0,
) -> pd.Series:
    """Expose the shared drawdown-based risk appetite for Chapter 9."""
    appetite = dynamic_risk_appetite(
        pd.Series(equity_curve, dtype=float),
        max_drawdown_tolerance=max_drawdown_tolerance,
        min_risk=min_risk,
        max_risk=max_risk,
        smoothing_span=smoothing_span,
        curve_shape=curve_shape,
        drawdown_window=drawdown_window,
    )
    return appetite.clip(lower=min_risk, upper=max_risk).rename("risk_appetite")


def temporary_boost(
    series1: pd.Series,
    series2: pd.Series,
    boost_val: float,
    duration: int,
) -> np.ndarray:
    """Boost one strategy when the other declines over the lookback period."""
    if duration < 1 or boost_val < 0:
        raise ValueError("duration must be positive and boost_val non-negative")
    cond1 = series1.pct_change(duration) < 0
    cond2 = series2.pct_change(duration) >= 0
    return np.where(cond1 & cond2, boost_val, 1.0)


def calculate_raw_weight(
    upper_band: float,
    boost: float,
    gross_exposure: float,
) -> float:
    """Calculate an un-clipped strategy weight."""
    if upper_band < 0 or boost < 0 or gross_exposure < 0:
        raise ValueError("weight inputs must be non-negative")
    return upper_band * boost * gross_exposure


def clip_weight(
    weight: float,
    upper_band: float,
    min_exposure: float,
    max_exposure: float,
) -> float:
    """Clip a strategy weight to its acceptable exposure range."""
    if upper_band < 0 or min_exposure < 0 or max_exposure < min_exposure:
        raise ValueError("exposure bounds are invalid")
    return float(np.clip(weight, upper_band * min_exposure, upper_band * max_exposure))


def calculate_portfolio_return(
    w_mr: float,
    w_tf: float,
    mr_return: float,
    tf_return: float,
) -> float:
    """Combine mean-reversion and trend-following strategy returns."""
    return w_mr * mr_return + w_tf * tf_return


def exposure_allocation(
    mr_returns: pd.Series,
    tf_returns: pd.Series,
    initial_capital: float,
    upper_band_mr: float,
    upper_band_tf: float,
    min_exposure: float,
    max_exposure: float,
    k: int,
    risk_params: dict[str, float],
    curve_shape: str = "linear",
    mr_boost_val: float = 2.0,
    tf_boost_val: float = 1.1,
) -> pd.DataFrame:
    """Recursively allocate exposure across mean reversion and trend following."""
    mr = pd.Series(mr_returns, dtype=float)
    tf = pd.Series(tf_returns, dtype=float)
    if len(mr) != len(tf):
        raise ValueError("return series must have the same length")
    if not mr.index.equals(tf.index):
        raise ValueError("return series must share the same index")
    if mr.empty:
        return pd.DataFrame(
            columns=[
                "equity",
                "w_MR",
                "w_TF",
                "portfolio_returns",
                "gross_exposure",
                "mr_boost",
                "tf_boost",
            ],
            index=mr.index,
        )
    if initial_capital <= 0 or k < 1:
        raise ValueError("initial_capital must be positive and k must be at least 1")
    if upper_band_mr < 0 or upper_band_tf < 0:
        raise ValueError("upper bands must be non-negative")
    if min_exposure < 0 or max_exposure < min_exposure:
        raise ValueError("exposure bounds are invalid")
    required = {"max_drawdown_tolerance", "min_risk", "max_risk"}
    missing = required.difference(risk_params)
    if missing:
        raise ValueError(f"risk_params missing keys: {sorted(missing)}")

    n = len(mr)
    equity = np.full(n, np.nan, dtype=float)
    equity[0] = initial_capital
    w_mr = np.full(n, np.nan, dtype=float)
    w_tf = np.full(n, np.nan, dtype=float)
    portfolio = np.full(n, np.nan, dtype=float)
    gross = np.full(n, np.nan, dtype=float)

    mr_boost = temporary_boost(tf, mr, mr_boost_val, k)
    tf_boost = temporary_boost(mr, tf, tf_boost_val, k)

    for t in range(1, n):
        gross_exposure = risk_appetite(
            equity[:t],
            curve_shape=curve_shape,
            **risk_params,
        ).iloc[-1]
        gross[t] = gross_exposure
        w_mr[t] = clip_weight(
            calculate_raw_weight(upper_band_mr, mr_boost[t], gross_exposure),
            upper_band_mr,
            min_exposure,
            max_exposure,
        )
        w_tf[t] = clip_weight(
            calculate_raw_weight(upper_band_tf, tf_boost[t], gross_exposure),
            upper_band_tf,
            min_exposure,
            max_exposure,
        )
        portfolio[t] = calculate_portfolio_return(
            w_mr[t],
            w_tf[t],
            mr.iloc[t],
            tf.iloc[t],
        )
        equity[t] = equity[t - 1] * (1 + portfolio[t])

    return pd.DataFrame(
        {
            "equity": equity,
            "w_MR": w_mr,
            "w_TF": w_tf,
            "portfolio_returns": portfolio,
            "gross_exposure": gross,
            "mr_boost": mr_boost,
            "tf_boost": tf_boost,
        },
        index=mr.index,
    )
