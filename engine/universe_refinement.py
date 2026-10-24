"""Chapter 7 universe-refinement utilities.

The chapter narrows a broad equity universe into a practical short universe
using liquidity, crowding, corporate-action, fundamental, valuation, and beta
filters.  The functions here operate on supplied tabular data so callers can
plug in their own market-data provider.
"""

from __future__ import annotations

import pandas as pd

DEFAULT_MIN_DAILY_VALUE_TRADED = 1_000_000.0
DEFAULT_MAX_SHORT_PCT_FLOAT = 0.50


def calculate_value_traded(
    average_volume: pd.Series,
    current_price: pd.Series,
    average_daily_volume_10_day: pd.Series | None = None,
) -> pd.Series:
    """Calculate average daily dollar value traded, preferring 10-day volume."""
    volume = (
        average_daily_volume_10_day if average_daily_volume_10_day is not None else average_volume
    )
    return (
        pd.to_numeric(volume, errors="coerce") * pd.to_numeric(current_price, errors="coerce")
    ).rename("value_traded")


def calculate_short_pct_float(
    shares_short: pd.Series,
    float_shares: pd.Series,
    reported_short_pct_float: pd.Series | None = None,
) -> pd.Series:
    """Calculate short interest as a fraction of float with a reported fallback."""
    calculated = pd.to_numeric(shares_short, errors="coerce").div(
        pd.to_numeric(float_shares, errors="coerce")
    )
    if reported_short_pct_float is not None:
        reported = pd.to_numeric(reported_short_pct_float, errors="coerce")
        calculated = calculated.fillna(reported)
    return calculated.rename("short_pct_float")


def rolling_beta(
    stock_returns: pd.Series,
    market_returns: pd.Series,
    window: int = 60,
) -> pd.Series:
    """Calculate rolling beta as covariance(stock, market) / market variance."""
    if window < 2:
        raise ValueError("window must be at least 2")
    stock, market = stock_returns.align(market_returns, join="inner")
    stock = pd.to_numeric(stock, errors="coerce")
    market = pd.to_numeric(market, errors="coerce")
    covariance = stock.rolling(window, min_periods=window).cov(market)
    variance = market.rolling(window, min_periods=window).var()
    return covariance.div(variance).rename("beta")


def sector_average_returns(
    returns: pd.DataFrame,
    sectors: pd.Series,
) -> pd.Series:
    """Calculate average security return by sector for aligned observations."""
    frame = returns.copy()
    frame.columns = pd.Index(frame.columns)
    sector_map = pd.Series(sectors, index=sectors.index)
    valid_columns = [column for column in frame.columns if column in sector_map.index]
    if not valid_columns:
        return pd.Series(dtype=float, name="average_return")
    grouped = frame[valid_columns].mean(axis=0).groupby(sector_map.loc[valid_columns]).mean()
    return grouped.rename("average_return").sort_values(ascending=False)


def refine_short_universe(
    universe: pd.DataFrame,
    min_value_traded: float = DEFAULT_MIN_DAILY_VALUE_TRADED,
    max_short_pct_float: float = DEFAULT_MAX_SHORT_PCT_FLOAT,
    max_forward_pe: float | None = None,
    max_trailing_pe: float | None = None,
    max_beta: float | None = None,
    require_fundamental_deterioration: bool = False,
) -> pd.DataFrame:
    """Filter a security universe into practical short candidates.

    Expected columns include value_traded, short_pct_float, dividend_yield,
    buyback, trailing_pe, forward_pe, beta, and fundamental_deterioration.
    Missing optional columns are ignored; this keeps the utility usable with
    partial provider datasets.
    """
    if min_value_traded <= 0:
        raise ValueError("min_value_traded must be positive")
    if not 0 <= max_short_pct_float <= 1:
        raise ValueError("max_short_pct_float must be between 0 and 1")
    for value, name in (
        (max_forward_pe, "max_forward_pe"),
        (max_trailing_pe, "max_trailing_pe"),
        (max_beta, "max_beta"),
    ):
        if value is not None and value <= 0:
            raise ValueError(f"{name} must be positive")

    result = universe.copy()

    if "value_traded" in result:
        result = result[result["value_traded"].ge(min_value_traded)]

    if "short_pct_float" in result:
        result = result[result["short_pct_float"].fillna(0).le(max_short_pct_float)]

    if "buyback" in result:
        result = result[~result["buyback"].fillna(False).astype(bool)]

    if max_forward_pe is not None and "forward_pe" in result:
        result = result[result["forward_pe"].isna() | result["forward_pe"].le(max_forward_pe)]

    if max_trailing_pe is not None and "trailing_pe" in result:
        result = result[result["trailing_pe"].isna() | result["trailing_pe"].le(max_trailing_pe)]

    if max_beta is not None and "beta" in result:
        result = result[result["beta"].isna() | result["beta"].le(max_beta)]

    if require_fundamental_deterioration:
        if "fundamental_deterioration" not in result:
            raise ValueError("fundamental_deterioration is required when its filter is enabled")
        result = result[result["fundamental_deterioration"].fillna(False).astype(bool)]

    return result.copy()


def add_universe_metrics(
    universe: pd.DataFrame,
    average_volume: pd.Series,
    current_price: pd.Series,
    average_daily_volume_10_day: pd.Series | None = None,
    shares_short: pd.Series | None = None,
    float_shares: pd.Series | None = None,
    reported_short_pct_float: pd.Series | None = None,
) -> pd.DataFrame:
    """Add the Chapter 7 liquidity and crowding metrics to a universe."""
    result = universe.copy()
    result["value_traded"] = calculate_value_traded(
        average_volume, current_price, average_daily_volume_10_day
    )
    if shares_short is not None and float_shares is not None:
        result["short_pct_float"] = calculate_short_pct_float(
            shares_short, float_shares, reported_short_pct_float
        )
    return result


def universe_refinement_report(
    universe: pd.DataFrame,
    **filters: float | bool | None,
) -> dict[str, int]:
    """Report universe size before and after Chapter 7 filtering."""
    refined = refine_short_universe(universe, **filters)
    return {
        "input_count": int(len(universe)),
        "output_count": int(len(refined)),
        "removed_count": int(len(universe) - len(refined)),
    }
