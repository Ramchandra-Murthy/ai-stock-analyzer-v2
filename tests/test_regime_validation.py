import numpy as np
import pandas as pd
import pytest

from engine.regime_validation import validate_market_regimes


def test_validation_summarizes_forward_returns_by_regime_and_horizon():
    index = pd.RangeIndex(8)
    close = pd.Series([100, 101, 102, 101, 99, 100, 100, 103], index=index)
    regimes = pd.Series(
        [
            "BULLISH",
            "BULLISH",
            "BEARISH",
            "BEARISH",
            "BEARISH",
            "RANGE / MIXED",
            "RANGE / MIXED",
            "BULLISH",
        ],
        index=index,
    )

    result = validate_market_regimes(close, regimes, horizons=(1, 2))

    assert len(result) == 6
    bullish_one = result.query("Regime == 'BULLISH' and Horizon == 1").iloc[0]
    assert bullish_one["Observations"] == 2
    assert bullish_one["Directional hit rate"] == pytest.approx(1.0)
    bearish_one = result.query("Regime == 'BEARISH' and Horizon == 1").iloc[0]
    assert bearish_one["Observations"] == 3
    assert bearish_one["Directional hit rate"] == pytest.approx(2 / 3)
    neutral_one = result.query("Regime == 'RANGE / MIXED' and Horizon == 1").iloc[0]
    assert np.isnan(neutral_one["Directional hit rate"])


def test_validation_omits_unobservable_final_horizon_rows():
    close = pd.Series([100.0, 101.0, 102.0, 103.0])
    regimes = pd.Series(["BULLISH"] * 4)

    result = validate_market_regimes(close, regimes, horizons=(2,))

    bullish = result.loc[result["Regime"].eq("BULLISH")].iloc[0]
    assert bullish["Observations"] == 2


@pytest.mark.parametrize("horizons", [(), (0,), (-1,), (1, 1), (True,)])
def test_validation_rejects_invalid_horizons(horizons):
    with pytest.raises(ValueError):
        validate_market_regimes(
            pd.Series([100.0, 101.0]),
            pd.Series(["BULLISH", "BEARISH"]),
            horizons=horizons,
        )


def test_validation_rejects_duplicate_or_unordered_indexes():
    close = pd.Series([100.0, 101.0], index=[1, 1])
    regimes = pd.Series(["BULLISH", "BEARISH"], index=[1, 1])

    with pytest.raises(ValueError, match="unique"):
        validate_market_regimes(close, regimes)


def test_validation_rejects_unknown_regime_label():
    with pytest.raises(ValueError, match="unsupported"):
        validate_market_regimes(
            pd.Series([100.0, 101.0]),
            pd.Series(["UP", "BEARISH"]),
            horizons=(1,),
        )


def test_validation_ignores_nonpositive_and_nonfinite_prices():
    close = pd.Series([100.0, np.inf, -1.0, 103.0, 104.0])
    regimes = pd.Series(["BULLISH"] * len(close))

    result = validate_market_regimes(close, regimes, horizons=(1,))

    bullish = result.loc[result["Regime"].eq("BULLISH")].iloc[0]
    assert bullish["Observations"] == 1
