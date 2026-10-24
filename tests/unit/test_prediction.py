import numpy as np
import pandas as pd

from modules.prediction import predict_prices


def test_predict_prices_rejects_missing_history():
    assert predict_prices(None) == []
    assert predict_prices(pd.DataFrame()) == []
    assert predict_prices(pd.DataFrame({"Open": [1, 2, 3]})) == []


def test_predict_prices_rejects_invalid_horizon():
    frame = pd.DataFrame({"Close": np.linspace(100, 120, 30)})
    assert predict_prices(frame, 0) == []
    assert predict_prices(frame, "bad") == []


def test_predict_prices_returns_requested_horizon():
    frame = pd.DataFrame({"Close": np.linspace(100, 120, 30)})
    forecast = predict_prices(frame, 10)

    assert len(forecast) == 10
    assert all(np.isfinite(forecast))
    assert all(price > 0 for price in forecast)
