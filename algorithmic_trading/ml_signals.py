"""Leakage-safe machine-learning signals (research only).

The classic ML-in-finance mistake is leaking the future into training. This module guards
against it in three ways:

* features at bar *t* use data up to and including *t* only;
* the label at bar *t* is the sign of the return over the next ``horizon`` bars, so a training
  row is only used if its whole label window ends before the test period starts, with an extra
  ``embargo`` gap (purging);
* predictions come from walk-forward windows (fit on the past, predict the next block), and the
  resulting signal is traded on the following bar by the standard backtester.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from algorithmic_trading.backtester import BacktestMetrics, run_backtest
from algorithmic_trading.strategy_lab import normalise_price_frame
from algorithmic_trading.trading_costs import IndiaEquityCostModel

MODELS = ("Logistic regression", "Gradient boosting")


def make_model(name: str):
    if name == "Logistic regression":
        return make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=500))
    if name == "Gradient boosting":
        return HistGradientBoostingClassifier(
            max_depth=3, learning_rate=0.05, max_iter=150, random_state=0
        )
    raise ValueError(f"Unknown model: {name}")


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return 100 - 100 / (1 + gain / loss.where(loss > 1e-12))


def build_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Causal features: momentum, volatility, trend distance, RSI, range and volume."""
    close = frame["Close"]
    ret = close.pct_change()
    feats = pd.DataFrame(index=frame.index)
    for n in (1, 5, 10, 21, 63):
        feats[f"ret_{n}"] = close.pct_change(n)
    feats["vol_20"] = ret.rolling(20).std()
    feats["vol_ratio"] = ret.rolling(5).std() / ret.rolling(60).std()
    feats["dist_sma50"] = close / close.rolling(50).mean() - 1.0
    feats["dist_sma200"] = close / close.rolling(200).mean() - 1.0
    feats["rsi_14"] = _rsi(close)
    feats["range_pct"] = (frame["High"] - frame["Low"]) / close
    if "Volume" in frame and frame["Volume"].gt(0).any():
        vol = frame["Volume"].astype(float)
        feats["volume_z"] = (vol - vol.rolling(20).mean()) / vol.rolling(20).std().where(
            lambda s: s > 0
        )
    # a feature that is never defined (e.g. constant volume) would blank out every row
    return feats.replace([np.inf, -np.inf], np.nan).dropna(axis=1, how="all")


def build_labels(close: pd.Series, horizon: int) -> pd.Series:
    """1 if the next-``horizon``-bar return is positive, 0 if not, NaN where unknown."""
    fwd = close.shift(-horizon) / close - 1.0
    return (fwd > 0).astype(float).where(fwd.notna())


@dataclass(frozen=True)
class MLResult:
    probabilities: pd.Series  # out-of-sample P(up), NaN before the first test window
    signals: pd.Series
    curve: pd.DataFrame
    metrics: BacktestMetrics
    accuracy: float  # out-of-sample directional accuracy
    base_rate: float  # share of up labels in the test periods (the naive benchmark)
    importances: pd.Series
    windows: int


def walk_forward_probabilities(
    feats: pd.DataFrame,
    labels: pd.Series,
    model_factory: Callable[[], object],
    *,
    train_bars: int = 756,
    test_bars: int = 63,
    horizon: int = 5,
    embargo: int = 5,
) -> tuple[pd.Series, list[tuple[int, int, int]]]:
    """Out-of-sample P(up). Returns (probabilities, [(train_start, train_end, test_start)])."""
    if train_bars < 200 or test_bars < 5 or horizon < 1 or embargo < 0:
        raise ValueError("train_bars >= 200, test_bars >= 5, horizon >= 1, embargo >= 0 required")
    n = len(feats)
    if n < train_bars + test_bars + horizon + embargo:
        raise ValueError("Not enough history for even one walk-forward window.")
    proba = pd.Series(np.nan, index=feats.index)
    spans = []
    for test_start in range(train_bars + horizon + embargo, n - 1, test_bars):
        train_end = test_start - horizon - embargo  # exclusive: labels end before test starts
        train_start = max(train_end - train_bars, 0)
        x = feats.iloc[train_start:train_end]
        y = labels.iloc[train_start:train_end]
        keep = x.notna().all(axis=1) & y.notna()
        if keep.sum() < 150 or y[keep].nunique() < 2:
            continue
        model = model_factory()
        model.fit(x[keep], y[keep])  # type: ignore[attr-defined]
        block = feats.iloc[test_start : test_start + test_bars]
        ok = block.notna().all(axis=1)
        if ok.any():
            proba.loc[block.index[ok]] = model.predict_proba(block[ok])[:, 1]  # type: ignore[attr-defined]
        spans.append((train_start, train_end, test_start))
    if not spans:
        raise ValueError("No usable walk-forward window (too little clean data).")
    return proba, spans


def run_ml_strategy(
    frame: pd.DataFrame,
    *,
    model: str = "Logistic regression",
    train_bars: int = 756,
    test_bars: int = 63,
    horizon: int = 5,
    embargo: int = 5,
    threshold: float = 0.55,
    cost_bps: float = 10.0,
    cost_model: IndiaEquityCostModel | None = None,
) -> MLResult:
    if not 0.5 <= threshold < 1:
        raise ValueError("threshold must be in [0.5, 1)")
    data = normalise_price_frame(frame)
    feats = build_features(data)
    labels = build_labels(data["Close"], horizon)
    proba, spans = walk_forward_probabilities(
        feats,
        labels,
        lambda: make_model(model),
        train_bars=train_bars,
        test_bars=test_bars,
        horizon=horizon,
        embargo=embargo,
    )
    signals = (proba > threshold).astype(float).where(proba.notna(), 0.0)
    curve, metrics = run_backtest(data["Close"], signals, cost_bps=cost_bps, cost_model=cost_model)
    scored = proba.notna() & labels.notna()
    accuracy = (
        float(((proba[scored] > 0.5).astype(float) == labels[scored]).mean())
        if scored.any()
        else 0.0
    )
    base = float(labels[scored].mean()) if scored.any() else 0.0
    # importances from one final model on the last training window (descriptive only)
    ts, te, _ = spans[-1]
    x, y = feats.iloc[ts:te], labels.iloc[ts:te]
    keep = x.notna().all(axis=1) & y.notna()
    final = make_model(model).fit(x[keep], y[keep])
    if model == "Logistic regression":
        importances = pd.Series(np.abs(final[-1].coef_[0]), index=feats.columns)
    else:
        from sklearn.inspection import permutation_importance

        pi = permutation_importance(final, x[keep], y[keep], n_repeats=3, random_state=0)
        importances = pd.Series(pi.importances_mean, index=feats.columns)
    return MLResult(
        proba,
        signals,
        curve,
        metrics,
        accuracy,
        max(base, 1 - base),
        importances.sort_values(ascending=False),
        len(spans),
    )
