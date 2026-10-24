import numpy as np
import pandas as pd
import pytest

from ai_trading.time_series_momentum import (
    best_time_series_momentum_pair,
    time_series_momentum_diagnostics,
)


@pytest.fixture
def momentum_returns() -> pd.Series:
    rng = np.random.default_rng(7)
    values = np.zeros(500)
    shocks = rng.normal(0.0, 0.01, len(values))
    for index in range(1, len(values)):
        values[index] = 0.004 + 0.35 * values[index - 1] + shocks[index]
    return pd.Series(values)


def test_time_series_momentum_reports_horizon_grid(
    momentum_returns: pd.Series,
) -> None:
    report = time_series_momentum_diagnostics(
        momentum_returns,
        lookbacks=(5, 20),
        holding_periods=(1, 5),
    )

    assert len(report) == 4
    assert set(report["lookback"]) == {5, 20}
    assert set(report["holding_period"]) == {1, 5}
    assert (report["observations"] > 0).all()
    assert report["return_correlation"].notna().all()
    assert report["sign_correlation"].notna().all()


def test_best_time_series_momentum_pair_returns_positive_relationship(
    momentum_returns: pd.Series,
) -> None:
    result = best_time_series_momentum_pair(
        momentum_returns,
        lookbacks=(5, 20),
        holding_periods=(1, 5),
    )

    assert result["lookback"] in {5, 20}
    assert result["holding_period"] in {1, 5}
    assert result["return_correlation"] is not None
    assert result["return_correlation"] > 0.0


@pytest.mark.parametrize(
    ("lookbacks", "holding_periods"),
    [
        ((), (1,)),
        ((0,), (1,)),
        ((1,), ()),
        ((1,), (0,)),
    ],
)
def test_time_series_momentum_validates_periods(
    momentum_returns: pd.Series,
    lookbacks: tuple[int, ...],
    holding_periods: tuple[int, ...],
) -> None:
    with pytest.raises(ValueError):
        time_series_momentum_diagnostics(
            momentum_returns,
            lookbacks=lookbacks,
            holding_periods=holding_periods,
        )


@pytest.mark.parametrize("bad_value", [float("inf"), float("-inf"), float("nan")])
def test_time_series_momentum_excludes_non_finite_returns(
    momentum_returns: pd.Series,
    bad_value: float,
) -> None:
    contaminated = pd.concat([momentum_returns, pd.Series([bad_value])], ignore_index=True)
    clean_report = time_series_momentum_diagnostics(
        momentum_returns,
        lookbacks=(5,),
        holding_periods=(1,),
    )
    contaminated_report = time_series_momentum_diagnostics(
        contaminated,
        lookbacks=(5,),
        holding_periods=(1,),
    )

    pd.testing.assert_frame_equal(contaminated_report, clean_report)


@pytest.mark.parametrize("bad_value", [-1.0, -1.1])
def test_time_series_momentum_rejects_returns_at_or_below_minus_one(
    momentum_returns: pd.Series,
    bad_value: float,
) -> None:
    contaminated = pd.concat([momentum_returns, pd.Series([bad_value])], ignore_index=True)

    with pytest.raises(ValueError, match="greater than -1.0"):
        time_series_momentum_diagnostics(contaminated, lookbacks=(5,), holding_periods=(1,))
