import pandas as pd
import pytest

from ai_trading.ensemble_model import predict_ensemble, train_ensemble


def _frame() -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=200, freq="D")
    close = [100.0 + (i % 40) * 2 if i % 80 < 40 else 100.0 - (i % 40) * 2 for i in range(200)]
    volume = [1000.0 + i * 10 for i in range(200)]
    return pd.DataFrame({"Close": close, "Volume": volume}, index=index)


def test_train_ensemble_uses_chronological_validation() -> None:
    models, validation = train_ensemble(_frame(), horizon=5, test_fraction=0.2)
    assert set(models) == {"logistic_regression", "random_forest"}
    assert validation.train_samples > validation.test_samples
    assert 0.0 <= validation.accuracy <= 1.0


def test_predict_ensemble_returns_bounded_probability() -> None:
    models, _ = train_ensemble(_frame(), horizon=5)
    prediction = predict_ensemble(models, _frame())
    assert 0.0 <= prediction["probability_up"] <= 1.0
    assert 0.0 <= prediction["confidence"] <= 1.0
    assert prediction["signal"] in {"LONG", "SHORT"}


def test_one_class_training_window_is_rejected() -> None:
    frame = _frame().assign(Close=lambda data: 100.0 + pd.RangeIndex(len(data)))
    with pytest.raises(ValueError, match="both target classes"):
        train_ensemble(frame, horizon=5)


def test_invalid_inputs_are_rejected() -> None:
    with pytest.raises(ValueError):
        train_ensemble(_frame(), test_fraction=0.05)
