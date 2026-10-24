import numpy as np
import pandas as pd
import pytest

from algorithmic_trading import ml_signals as ml


def _frame(n=1500, seed=0, signal=0.0):
    """Random walk; with signal>0 the next-day return depends on today's 1-day return (AR)."""
    rng = np.random.default_rng(seed)
    r = np.zeros(n)
    for t in range(1, n):
        r[t] = signal * r[t - 1] + rng.normal(0.0003, 0.01)
    close = 100 * np.exp(np.cumsum(r))
    idx = pd.bdate_range("2017-01-01", periods=n)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.004,
            "Low": close * 0.996,
            "Close": close,
            "Volume": rng.integers(1e5, 2e5, n),
        },
        index=idx,
    )


def test_features_are_causal():
    f = _frame(600)
    full = ml.build_features(f)
    pd.testing.assert_frame_equal(full.iloc[:400], ml.build_features(f.iloc[:400]))
    altered = f.copy()
    altered.iloc[450:, :4] *= 3
    pd.testing.assert_frame_equal(full.iloc[:450], ml.build_features(altered).iloc[:450])


def test_labels_hand_computed_and_nan_tail():
    close = pd.Series([100.0, 101, 99, 102, 98, 97])
    y = ml.build_labels(close, 2)
    assert y.iloc[:4].tolist() == [
        0.0,
        1.0,
        0.0,
        0.0,
    ]  # 100->99 down, 101->102 up, 99->98 down, 102->97 down
    assert y.iloc[4:].isna().all()


def test_training_windows_end_before_test_labels_could_overlap():
    f = _frame(1200)
    feats, labels = ml.build_features(f), ml.build_labels(f["Close"], 5)
    seen = []

    class Spy:
        def fit(self, x, y):
            seen.append((x.index.max(), y.index.max()))
            return self

        def predict_proba(self, x):
            return np.tile([0.5, 0.5], (len(x), 1))

    _, spans = ml.walk_forward_probabilities(
        feats, labels, Spy, train_bars=500, test_bars=63, horizon=5, embargo=5
    )
    for (_ts, te, test_start), (last_x, _) in zip(spans, seen, strict=True):
        assert te <= test_start - 10
        # the last training label (at te-1) looks 5 bars ahead -> must end before the test start
        assert feats.index.get_loc(last_x) + 5 < test_start


def test_predictions_do_not_change_when_data_after_the_window_is_rewritten():
    f = _frame(1400)
    base = ml.run_ml_strategy(f, train_bars=500, test_bars=63).probabilities
    altered = f.copy()
    cut = 1100
    altered.iloc[cut:, :4] *= np.linspace(1, 3, len(f) - cut)[:, None]
    changed = ml.run_ml_strategy(altered, train_bars=500, test_bars=63).probabilities
    # windows whose test block (and 10-bar purge) end before the cut are untouched
    safe = base.index[: cut - 63 - 10]
    pd.testing.assert_series_equal(base.loc[safe], changed.loc[safe])


def test_noise_gives_no_edge_but_planted_signal_is_found():
    noise = ml.run_ml_strategy(
        _frame(1800, seed=1), train_bars=600, test_bars=63, horizon=1, embargo=1
    )
    assert abs(noise.accuracy - noise.base_rate) < 0.06
    planted = ml.run_ml_strategy(
        _frame(1800, seed=2, signal=0.35), train_bars=600, test_bars=63, horizon=1, embargo=1
    )
    assert planted.accuracy > 0.53
    assert planted.accuracy > planted.base_rate - 0.02
    assert planted.importances.index[0] in ("ret_1", "ret_5")


def test_first_window_has_no_trades_and_costs_reduce_results():
    f = _frame(1500, seed=3, signal=0.3)
    free = ml.run_ml_strategy(
        f, train_bars=500, test_bars=63, horizon=1, embargo=1, cost_bps=0, threshold=0.5
    )
    costly = ml.run_ml_strategy(
        f, train_bars=500, test_bars=63, horizon=1, embargo=1, cost_bps=40, threshold=0.5
    )
    assert (free.signals.iloc[:500] == 0).all()
    assert costly.metrics.total_return <= free.metrics.total_return


def test_gradient_boosting_runs_and_validation():
    r = ml.run_ml_strategy(
        _frame(1100, seed=4), model="Gradient boosting", train_bars=400, test_bars=100
    )
    assert r.windows >= 3 and r.probabilities.dropna().between(0, 1).all()
    with pytest.raises(ValueError):
        ml.run_ml_strategy(_frame(1100), model="magic")
    with pytest.raises(ValueError):
        ml.run_ml_strategy(_frame(1100), threshold=0.2)
    with pytest.raises(ValueError):
        ml.run_ml_strategy(_frame(500), train_bars=756)
    with pytest.raises(ValueError):
        ml.walk_forward_probabilities(
            ml.build_features(_frame(900)),
            ml.build_labels(_frame(900)["Close"], 5),
            lambda: ml.make_model("Logistic regression"),
            train_bars=50,
        )


def test_undefined_feature_columns_do_not_blank_out_every_row():
    f = _frame(900)
    f["Volume"] = 100_000  # constant volume -> z-score undefined everywhere
    feats = ml.build_features(f)
    assert "volume_z" not in feats and feats.dropna().shape[0] > 500
