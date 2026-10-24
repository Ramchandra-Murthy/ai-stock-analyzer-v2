"""Pairs-trading research: Engle-Granger cointegration, hedge ratio, half-life, spread backtest.

Statistical-arbitrage ideas are fragile: relationships break, and shorting one leg is not
available to most Indian retail investors in the cash market (it needs futures or intraday
positions). This module is for research only.

Method: formation window -> OLS hedge ratio on log prices -> Engle-Granger test (ADF on the
residual, with MacKinnon critical values for a two-variable test with a constant) ->
half-life. The trading test then runs on the data AFTER the formation window with the hedge
ratio frozen, so the test is out of sample for the relationship itself.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Asymptotic MacKinnon (1991/2010) critical values, Engle-Granger, 2 variables, constant.
EG_CRITICAL = {0.01: -3.90, 0.05: -3.34, 0.10: -3.04}
TRADING_DAYS = 252


@dataclass(frozen=True)
class CointegrationResult:
    beta: float
    alpha: float
    adf_stat: float
    critical_5pct: float
    cointegrated_5pct: bool
    cointegrated_10pct: bool
    half_life: float | None
    n_obs: int


def adf_statistic(series: np.ndarray, lags: int = 1) -> float:
    """t-statistic on gamma in  d_e[t] = gamma*e[t-1] + sum_i phi_i*d_e[t-i] + u  (no constant)."""
    e = np.asarray(series, dtype=float)
    d = np.diff(e)
    n = len(d) - lags
    if n < 20:
        raise ValueError("Not enough observations for the ADF test.")
    y = d[lags:]
    cols = [e[lags : len(e) - 1]]
    for i in range(1, lags + 1):
        cols.append(d[lags - i : len(d) - i])
    x = np.column_stack(cols)
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    resid = y - x @ coef
    sigma2 = resid @ resid / (len(y) - x.shape[1])
    cov = sigma2 * np.linalg.inv(x.T @ x)
    return float(coef[0] / np.sqrt(cov[0, 0]))


def half_life(spread: np.ndarray) -> float | None:
    """Mean-reversion half-life in bars from  d_s = a + b*s[t-1];  None if not mean reverting."""
    s = np.asarray(spread, dtype=float)
    x = np.column_stack([np.ones(len(s) - 1), s[:-1]])
    coef, *_ = np.linalg.lstsq(x, np.diff(s), rcond=None)
    b = coef[1]
    if b >= 0 or b <= -1:
        return None
    return float(-np.log(2.0) / np.log(1.0 + b))


def engle_granger(y: pd.Series, x: pd.Series, lags: int = 1) -> CointegrationResult:
    """Regress y on x (levels) and test the residual for a unit root."""
    both = pd.concat([y, x], axis=1).dropna()
    if len(both) < 60:
        raise ValueError("At least 60 aligned observations are needed.")
    yy, xx = both.iloc[:, 0].to_numpy(float), both.iloc[:, 1].to_numpy(float)
    design = np.column_stack([np.ones(len(xx)), xx])
    (alpha, beta), *_ = np.linalg.lstsq(design, yy, rcond=None)
    resid = yy - alpha - beta * xx
    stat = adf_statistic(resid, lags)
    return CointegrationResult(
        beta=float(beta),
        alpha=float(alpha),
        adf_stat=stat,
        critical_5pct=EG_CRITICAL[0.05],
        cointegrated_5pct=stat < EG_CRITICAL[0.05],
        cointegrated_10pct=stat < EG_CRITICAL[0.10],
        half_life=half_life(resid),
        n_obs=len(both),
    )


def spread_zscore(spread: pd.Series, window: int) -> pd.Series:
    """Rolling z-score using only the trailing ``window`` bars up to and including t."""
    mean = spread.rolling(window, min_periods=window).mean()
    std = spread.rolling(window, min_periods=window).std(ddof=1)
    return (spread - mean) / std.where(std > 1e-12)


def pair_signals(
    z: pd.Series, entry: float = 2.0, exit_: float = 0.5, stop: float = 4.0
) -> pd.Series:
    """Spread position: +1 long spread (z low), -1 short spread (z high), 0 flat."""
    if not 0 <= exit_ < entry < stop:
        raise ValueError("need 0 <= exit < entry < stop")
    pos = 0.0
    out = np.zeros(len(z))
    for i, v in enumerate(z.to_numpy(float)):
        if np.isnan(v):
            pos = 0.0
        elif abs(v) >= stop:
            pos = 0.0
        elif pos == 0.0:
            pos = 1.0 if v <= -entry else -1.0 if v >= entry else 0.0
        elif (pos > 0 and v >= -exit_) or (pos < 0 and v <= exit_):
            pos = 0.0
        out[i] = pos
    return pd.Series(out, index=z.index)


@dataclass(frozen=True)
class PairsResult:
    formation: CointegrationResult
    spread: pd.Series
    zscore: pd.Series
    position: pd.Series
    returns: pd.Series
    equity: pd.Series
    metrics: dict[str, float]
    trades: int


def backtest_pair(
    price_y: pd.Series,
    price_x: pd.Series,
    *,
    formation_fraction: float = 0.5,
    z_window: int | None = None,
    entry: float = 2.0,
    exit_: float = 0.5,
    stop: float = 4.0,
    cost_bps: float = 10.0,
) -> PairsResult:
    """Fit on the first part, trade the rest with the hedge ratio frozen."""
    if not 0.2 <= formation_fraction <= 0.8 or cost_bps < 0:
        raise ValueError("formation_fraction must be in [0.2, 0.8] and cost_bps non-negative")
    data = pd.concat([price_y, price_x], axis=1).dropna()
    data = data[(data > 0).all(axis=1)]
    if len(data) < 150:
        raise ValueError("At least 150 aligned prices are needed.")
    ly, lx = np.log(data.iloc[:, 0]), np.log(data.iloc[:, 1])
    cut = int(len(data) * formation_fraction)
    fit = engle_granger(ly.iloc[:cut], lx.iloc[:cut])
    spread = ly - fit.alpha - fit.beta * lx
    window = z_window or int(np.clip(round(2 * (fit.half_life or 20)), 10, 60))
    z = spread_zscore(spread, window)
    signal = pair_signals(z, entry, exit_, stop)
    position = signal.shift(1).fillna(0.0)
    position.iloc[:cut] = 0.0  # no trading inside the formation window
    ry, rx = data.iloc[:, 0].pct_change().fillna(0.0), data.iloc[:, 1].pct_change().fillna(0.0)
    gross = 1.0 + abs(fit.beta)
    pnl = position * (ry - fit.beta * rx) / gross
    cost = position.diff().abs().fillna(position.abs()) * (cost_bps / 10_000.0)
    returns = (pnl - cost).iloc[cut:]
    equity = (1.0 + returns).cumprod()
    std = float(returns.std(ddof=1))
    days = max((returns.index[-1] - returns.index[0]).days, 1)
    metrics = {
        "total_return": float(equity.iloc[-1] - 1.0),
        "cagr": float(equity.iloc[-1] ** (365.25 / days) - 1.0) if equity.iloc[-1] > 0 else -1.0,
        "sharpe": float(returns.mean() / std * np.sqrt(TRADING_DAYS)) if std > 1e-12 else 0.0,
        "max_drawdown": float((equity / equity.cummax() - 1.0).min()),
    }
    entries = int(((position != 0) & (position.shift(1).fillna(0.0) == 0)).iloc[cut:].sum())
    return PairsResult(fit, spread, z, position, returns, equity, metrics, entries)


def scan_pairs(
    prices: pd.DataFrame, pairs: list[tuple[str, str]], cut_fraction: float = 0.5
) -> pd.DataFrame:
    """Cointegration test of each pair on the formation window only."""
    rows = []
    for a, b in pairs:
        if a not in prices or b not in prices:
            continue
        both = np.log(prices[[a, b]].dropna())
        cut = int(len(both) * cut_fraction)
        try:
            r = engle_granger(both[a].iloc[:cut], both[b].iloc[:cut])
        except ValueError:
            continue
        rows.append(
            {
                "pair": f"{a} / {b}",
                "adf": r.adf_stat,
                "5% cointegrated": r.cointegrated_5pct,
                "hedge ratio": r.beta,
                "half-life (days)": r.half_life,
            }
        )
    return pd.DataFrame(rows).sort_values("adf") if rows else pd.DataFrame()


BANK_PAIRS = [
    ("HDFCBANK", "ICICIBANK"),
    ("SBIN", "BANKBARODA"),
    ("KOTAKBANK", "AXISBANK"),
    ("TCS", "INFY"),
    ("INFY", "WIPRO"),
    ("HINDUNILVR", "ITC"),
]
