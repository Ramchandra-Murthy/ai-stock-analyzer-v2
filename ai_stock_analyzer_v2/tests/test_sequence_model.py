import numpy as np
import pandas as pd
import pytest

from ai_trading.sequence_model import (
    make_sequences,
    predict_sequence,
    train_sequence_model,
)


def _frame() -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=220, freq="D")
    close = [100.0 + (i % 40) * 2 if i % 80 < 40 else 100.0 - (i % 40) * 2 for i in range(220)]
    volume = [1000.0 + i * 10 for i in range(220)]
    return pd.DataFrame({"Close": close, "Volume": volume}, index=index)


def test_make_sequences_shape() -> None:
    x, y = make_sequences(_frame(), sequence_length=20, horizon=5)
    assert x.ndim == 3
    assert x.shape[1:] == (20, 6)
    assert len(x) == len(y)


def test_train_sequence_model_uses_chronological_validation() -> None:
    trained, validation = train_sequence_model(_frame(), sequence_length=20)
    assert "model" in trained
    assert "scaler" in trained
    assert validation.train_samples > validation.test_samples
    assert 0.0 <= validation.accuracy <= 1.0


def test_predict_sequence_returns_bounded_probability() -> None:
    trained, _ = train_sequence_model(_frame(), sequence_length=20)
    prediction = predict_sequence(trained, _frame(), sequence_length=20)
    assert 0.0 <= prediction["probability_up"] <= 1.0
    assert 0.0 <= prediction["confidence"] <= 1.0
    assert prediction["signal"] in {"LONG", "SHORT"}


def test_sequence_scaler_is_fit_only_on_purged_training_sequences() -> None:
    from ai_trading.sequence_model import _make_raw_sequences

    frame = _frame()
    sequence_length = 20
    horizon = 5
    x, _, positions = _make_raw_sequences(
        frame,
        sequence_length=sequence_length,
        horizon=horizon,
        threshold=0.0,
    )
    split = max(1, int(len(x) * 0.8))
    train_mask = positions[:split] + horizon < positions[split]
    expected_mean = x[:split][train_mask].reshape(-1, x.shape[-1]).mean(axis=0)

    trained, _ = train_sequence_model(
        frame,
        sequence_length=sequence_length,
        horizon=horizon,
    )

    assert np.allclose(trained["scaler"].mean_, expected_mean)


def test_invalid_sequence_length() -> None:
    with pytest.raises(ValueError):
        make_sequences(_frame(), sequence_length=1)
