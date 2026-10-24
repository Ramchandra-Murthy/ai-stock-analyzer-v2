"""Walk-forward parameter optimisation for the Strategy Lab strategies.

Picking the best-looking parameters on all the history and then reporting how well they did
on that same history is the classic way to fool yourself. This module does it honestly:

1. Split history into rolling (train, test) windows.
2. In each window, choose the parameter set with the best score on the *train* slice only.
3. Record how that choice performed on the *test* slice it never saw.
4. Stitch the test slices together: that out-of-sample curve is the honest result.

Efficiency and correctness: every strategy signal at bar *t* uses data up to *t* only, so one
full-history backtest per parameter set is enough. Window scoring then just slices that return
series, and a window's choice can depend only on returns up to the end of its train slice.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from algorithmic_trading.strategy_lab import normalise_price_frame, run_strategy_lab
from algorithmic_trading.trading_costs import IndiaEquityCostModel

TRADING_DAYS = 252

# Parameter names match ``strategy_lab.build_signals``. Ensemble is not tuned: it combines the
# four tuned strategies at their defaults.
PARAM_GRIDS: dict[str, dict[str, list[float]]] = {
    "Supertrend": {"st_period": [7, 10, 14, 20], "st_multiplier": [2.0, 2.5, 3.0, 4.0]},
    "Donchian breakout": {"dc_entry": [10, 20, 40, 55], "dc_exit": [5, 10, 20]},
    "Z-score mean reversion": {"z_window": [10, 20, 40, 60], "z_entry": [1.5, 2.0, 2.5]},
    "RSI(2) pullback": {"rsi_oversold": [5, 10, 15, 20], "rsi_trend": [100, 150, 200]},
}

ParamKey = tuple[tuple[str, float], ...]


def _key(params: Mapping[str, float]) -> ParamKey:
    return tuple(sorted((name, float(value)) for name, value in params.items()))


def _label(key: ParamKey | None) -> str:
    if key is None:
        return "flat (nothing qualified)"
    return ", ".join(f"{name}={value:g}" for name, value in key)


def parameter_combinations(strategy: str) -> list[dict[str, float]]:
    """All valid parameter sets for ``strategy`` (exit windows must be shorter than entry)."""
    if strategy not in PARAM_GRIDS:
        raise ValueError(f"No parameter grid for strategy: {strategy}")
    grid = PARAM_GRIDS[strategy]
    names = list(grid)
    combos = [dict(zip(names, values, strict=True)) for values in itertools.product(*grid.values())]
    if strategy == "Donchian breakout":
        combos = [c for c in combos if c["dc_exit"] < c["dc_entry"]]
    return combos


# --------------------------------------------------------------------------------------
# scoring helpers
# --------------------------------------------------------------------------------------
def sharpe(returns: pd.Series) -> float:
    """Annualised Sharpe ratio of daily returns (0 if there is no variation)."""
    values = pd.to_numeric(returns, errors="coerce").dropna()
    if len(values) < 2:
        return 0.0
    std = float(values.std(ddof=1))
    if std <= 1e-12:
        return 0.0
    return float(values.mean() / std * np.sqrt(TRADING_DAYS))


def returns_summary(returns: pd.Series) -> dict[str, float]:
    """Total return, CAGR, Sharpe and max drawdown of a daily return series."""
    values = pd.to_numeric(returns, errors="coerce").fillna(0.0)
    if values.empty:
        return {"total_return": 0.0, "cagr": 0.0, "sharpe": 0.0, "max_drawdown": 0.0}
    equity = (1.0 + values).cumprod()
    total = float(equity.iloc[-1] - 1.0)
    days = max((values.index[-1] - values.index[0]).days, 1)
    cagr = float(equity.iloc[-1] ** (365.25 / days) - 1.0) if equity.iloc[-1] > 0 else -1.0
    drawdown = equity / equity.cummax() - 1.0
    return {
        "total_return": total,
        "cagr": cagr,
        "sharpe": sharpe(values),
        "max_drawdown": float(drawdown.min()),
    }


def _active_changes(positions: pd.Series) -> int:
    return int(positions.diff().abs().fillna(positions.abs()).gt(0).sum())


# --------------------------------------------------------------------------------------
# core selection logic (pure, deterministic, unit-testable with crafted returns)
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class WalkForwardResult:
    strategy: str
    windows: pd.DataFrame  # one row per window
    oos_returns: pd.Series  # stitched out-of-sample daily returns
    buy_hold_returns: pd.Series  # buy and hold over the same out-of-sample dates
    oos: dict[str, float]
    buy_hold: dict[str, float]
    mean_train_sharpe: float
    mean_test_sharpe: float
    parameter_stability: float  # share of windows that chose the most common parameter set


def make_windows(
    n: int, train_bars: int, test_bars: int, step: int | None = None, anchored: bool = False
) -> list[tuple[int, int, int, int]]:
    """(train_start, train_end, test_start, test_end) index tuples, end-exclusive."""
    if train_bars < 20 or test_bars < 5:
        raise ValueError("train_bars must be >= 20 and test_bars >= 5")
    step = step or test_bars
    windows = []
    test_start = train_bars
    while test_start + test_bars <= n:
        train_start = 0 if anchored else test_start - train_bars
        windows.append((train_start, test_start, test_start, test_start + test_bars))
        test_start += step
    return windows


def select_and_evaluate(
    returns_by_params: Mapping[ParamKey, pd.Series],
    positions_by_params: Mapping[ParamKey, pd.Series],
    market_returns: pd.Series,
    windows: list[tuple[int, int, int, int]],
    *,
    min_changes: int = 3,
    strategy: str = "",
) -> WalkForwardResult:
    """Choose per window on the train slice only, then score on the test slice."""
    if not windows:
        raise ValueError("Not enough history for even one train/test window.")
    index = market_returns.index
    rows = []
    oos_parts = []
    chosen_keys: list[ParamKey | None] = []

    for number, (a, b, c, d) in enumerate(windows, start=1):
        best_key: ParamKey | None = None
        best_score = -np.inf
        for key, series in returns_by_params.items():
            if _active_changes(positions_by_params[key].iloc[a:b]) < min_changes:
                continue  # a strategy that barely trades is not evidence of skill
            score = sharpe(series.iloc[a:b])
            if score > best_score:
                best_key, best_score = key, score
        chosen_keys.append(best_key)

        if best_key is None:
            test_returns = pd.Series(0.0, index=index[c:d])
            train_score = 0.0
        else:
            test_returns = returns_by_params[best_key].iloc[c:d]
            train_score = best_score
        oos_parts.append(test_returns)
        rows.append(
            {
                "window": number,
                "train_start": index[a],
                "train_end": index[b - 1],
                "test_start": index[c],
                "test_end": index[d - 1],
                "chosen_parameters": _label(best_key),
                "train_sharpe": train_score,
                "test_sharpe": sharpe(test_returns),
                "test_return": float((1.0 + test_returns).prod() - 1.0),
            }
        )

    oos = pd.concat(oos_parts)
    oos = oos[~oos.index.duplicated(keep="first")]
    table = pd.DataFrame(rows)
    counts = pd.Series([k for k in chosen_keys if k is not None], dtype=object).value_counts()
    stability = float(counts.iloc[0] / len(chosen_keys)) if len(counts) else 0.0
    return WalkForwardResult(
        strategy=strategy,
        windows=table,
        oos_returns=oos,
        buy_hold_returns=market_returns.reindex(oos.index).fillna(0.0),
        oos=returns_summary(oos),
        buy_hold=returns_summary(market_returns.reindex(oos.index).fillna(0.0)),
        mean_train_sharpe=float(table["train_sharpe"].mean()),
        mean_test_sharpe=float(table["test_sharpe"].mean()),
        parameter_stability=stability,
    )


# --------------------------------------------------------------------------------------
# public entry points
# --------------------------------------------------------------------------------------
def _full_history_runs(
    frame: pd.DataFrame,
    strategy: str,
    combos: list[dict[str, float]],
    *,
    cost_bps: float,
    cost_model: IndiaEquityCostModel | None,
    allow_short: bool,
) -> tuple[dict[ParamKey, pd.Series], dict[ParamKey, pd.Series], pd.Series]:
    returns: dict[ParamKey, pd.Series] = {}
    positions: dict[ParamKey, pd.Series] = {}
    market = frame["Close"].pct_change().fillna(0.0)
    for params in combos:
        result = run_strategy_lab(
            frame,
            strategy,
            cost_bps=cost_bps,
            cost_model=cost_model,
            allow_short=allow_short,
            params=params,
        )
        returns[_key(params)] = result.curve["strategy_return"].reindex(frame.index).fillna(0.0)
        positions[_key(params)] = result.curve["position"].reindex(frame.index).fillna(0.0)
    return returns, positions, market


def walk_forward_optimize(
    frame: pd.DataFrame,
    strategy: str,
    *,
    train_bars: int = 504,
    test_bars: int = 126,
    anchored: bool = False,
    cost_bps: float = 10.0,
    cost_model: IndiaEquityCostModel | None = None,
    allow_short: bool = False,
    min_changes: int = 3,
) -> WalkForwardResult:
    """Rolling walk-forward optimisation of ``strategy`` on an OHLC frame."""
    data = normalise_price_frame(frame)
    combos = parameter_combinations(strategy)
    returns, positions, market = _full_history_runs(
        data,
        strategy,
        combos,
        cost_bps=cost_bps,
        cost_model=cost_model,
        allow_short=allow_short,
    )
    windows = make_windows(len(data), train_bars, test_bars, anchored=anchored)
    return select_and_evaluate(
        returns, positions, market, windows, min_changes=min_changes, strategy=strategy
    )


def parameter_surface(
    frame: pd.DataFrame,
    strategy: str,
    x_param: str,
    y_param: str,
    *,
    cost_bps: float = 10.0,
    cost_model: IndiaEquityCostModel | None = None,
    allow_short: bool = False,
    metric: Callable[[pd.Series], float] = sharpe,
) -> pd.DataFrame:
    """Full-history score for every (x, y) pair in the grid: rows are y, columns are x.

    A strategy worth trusting scores reasonably across a neighbourhood of settings; one lucky
    cell surrounded by poor ones is overfitting.
    """
    grid = PARAM_GRIDS[strategy]
    if x_param not in grid or y_param not in grid or x_param == y_param:
        raise ValueError("x_param and y_param must be two different parameters of the strategy")
    data = normalise_price_frame(frame)
    defaults = {name: values[len(values) // 2] for name, values in grid.items()}
    surface = pd.DataFrame(index=grid[y_param], columns=grid[x_param], dtype=float)
    for y in grid[y_param]:
        for x in grid[x_param]:
            params = {**defaults, x_param: x, y_param: y}
            if strategy == "Donchian breakout" and params["dc_exit"] >= params["dc_entry"]:
                continue  # invalid combination stays NaN
            result = run_strategy_lab(
                data,
                strategy,
                cost_bps=cost_bps,
                cost_model=cost_model,
                allow_short=allow_short,
                params=params,
            )
            surface.loc[y, x] = metric(result.curve["strategy_return"])
    surface.index.name, surface.columns.name = y_param, x_param
    return surface


def surface_robustness(surface: pd.DataFrame) -> dict[str, float]:
    """How broad the profitable region is: share of positive cells and the best cell's margin."""
    values = surface.to_numpy(dtype=float).ravel()
    values = values[~np.isnan(values)]
    if values.size == 0:
        return {"share_positive": 0.0, "best": 0.0, "median": 0.0}
    return {
        "share_positive": float((values > 0).mean()),
        "best": float(values.max()),
        "median": float(np.median(values)),
    }
