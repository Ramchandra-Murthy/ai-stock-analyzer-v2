import numpy as np
import pandas as pd
import pytest

from engine.position_sizing import (
    atr_position_size,
    average_true_range,
    fixed_dollar_size,
    fixed_risk_size,
    kelly_position_size,
    position_sizing_report,
    rolling_volatility,
    volatility_size,
)


def test_fixed_dollar_and_fixed_risk_sizing():
    assert fixed_dollar_size(100000, 0.10, 500) == pytest.approx(20)
    assert fixed_risk_size(100000, 0.01, 500, 450) == pytest.approx(20)


def test_volatility_atr_and_kelly_sizing():
    assert volatility_size(100000, 0.10, 0.20, 500) == pytest.approx(100)
    assert atr_position_size(100000, 0.01, 25) == pytest.approx(40)
    assert kelly_position_size(100000, 0.25, 500) == pytest.approx(50)


def test_kelly_can_be_capped():
    assert kelly_position_size(100000, 0.40, 500, max_fraction=0.20) == pytest.approx(40)


def test_rolling_volatility_and_atr():
    returns = pd.Series(np.linspace(-0.02, 0.02, 10))
    volatility = rolling_volatility(returns, window=5, annualize=False)
    assert volatility.iloc[:4].isna().all()
    assert volatility.iloc[-1] == pytest.approx(returns.iloc[5:10].std())

    high = pd.Series([101, 103, 104, 106, 108], dtype=float)
    low = pd.Series([99, 100, 101, 103, 105], dtype=float)
    close = pd.Series([100, 102, 103, 105, 107], dtype=float)
    atr = average_true_range(high, low, close, window=3)
    assert atr.iloc[:2].isna().all()
    assert atr.iloc[-1] == pytest.approx(3.0)


def test_report_contains_all_sizing_methods():
    report = position_sizing_report(100000, 500, 0.01, 450, 25, 0.20, 0.25)
    assert set(report) == {"fixed_dollar", "fixed_risk", "atr", "volatility", "kelly"}


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        fixed_dollar_size(100000, 1.1, 500)
    with pytest.raises(ValueError):
        fixed_risk_size(100000, 0.01, 500, 500)
    with pytest.raises(ValueError):
        volatility_size(100000, 0.10, 0, 500)
    with pytest.raises(ValueError):
        atr_position_size(100000, 0.01, 0)
    with pytest.raises(ValueError):
        kelly_position_size(100000, -0.1, 500)
