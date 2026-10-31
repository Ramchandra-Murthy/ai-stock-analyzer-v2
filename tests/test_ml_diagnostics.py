import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from algorithmic_trading.ml_diagnostics import (
    diagnose_model,
    overfit_verdict,
    permutation_importance_oos,
    time_series_grid_search,
)


def _data(n=600, seed=0):
    rng = np.random.default_rng(seed)
    x = pd.DataFrame({"signal": rng.normal(size=n), "noise": rng.normal(size=n)})
    y = pd.Series((x["signal"] + rng.normal(0, 0.3, n) > 0).astype(int))
    return x, y


def test_permutation_importance_finds_the_real_feature():
    x, y = _data()
    model = LogisticRegression().fit(x.iloc[:400], y.iloc[:400])
    imp = permutation_importance_oos(model, x.iloc[400:], y.iloc[400:], n_repeats=5)
    assert imp.index[0] == "signal" and imp.loc["signal", "importance"] > 0.2
    assert abs(imp.loc["noise", "importance"]) < 0.05


def test_grid_search_ranks_and_reports_train_gap():
    x, y = _data()
    grid = time_series_grid_search(
        lambda C: LogisticRegression(C=C), {"C": [0.001, 1.0]}, x, y, n_splits=3, gap=5
    )
    assert list(grid.columns) == ["C", "cv_accuracy", "cv_std", "train_accuracy"]
    assert grid["cv_accuracy"].is_monotonic_decreasing and len(grid) == 2


def test_verdicts():
    assert "Severe" in overfit_verdict(0.95, 0.52, 0.5)
    assert "Moderate" in overfit_verdict(0.62, 0.53, 0.5)
    assert "No real edge" in overfit_verdict(0.52, 0.505, 0.5)
    assert "measurable edge" in overfit_verdict(0.58, 0.56, 0.5)


def test_bad_inputs():
    x, y = _data(100)
    with pytest.raises(ValueError):
        time_series_grid_search(lambda C: LogisticRegression(C=C), {"C": [1]}, x, y, n_splits=4)
    with pytest.raises(ValueError):
        permutation_importance_oos(LogisticRegression().fit(x, y), x.iloc[:10], y.iloc[:10])
    with pytest.raises(ValueError):
        diagnose_model(pd.DataFrame(), model="nope")


def test_diagnose_model_end_to_end_on_a_random_walk_has_no_large_edge():
    rng = np.random.default_rng(7)
    n = 1500
    close = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
    frame = pd.DataFrame(
        {"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 1e6},
        index=pd.bdate_range("2018-01-01", periods=n),
    )
    d = diagnose_model(frame, n_repeats=2)
    assert d.test_accuracy < d.base_rate + 0.06  # nothing to find in a pure random walk
    assert d.train_rows > d.test_rows > 100 and "C" in d.best_params
