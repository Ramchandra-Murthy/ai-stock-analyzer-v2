import numpy as np
import pandas as pd
import pytest

from ai_trading.mean_reversion_strategy import mean_reversion_signals


def test_mean_reversion_signal_positions_are_next_bar_aligned() -> None:
    spread = pd.Series([0.0] * 20 + [-3.0, -4.0, -3.5, -2.0, -0.2, 0.0, 0.1])
    report = mean_reversion_signals(spread, lookback=5, entry_z=1.0, exit_z=0.2)

    assert set(report["position"].unique()).issubset({-1, 0, 1})
    pd.testing.assert_series_equal(
        report["position"],
        report["signal"].shift(1).fillna(0).astype(int),
        check_names=False,
    )


def test_mean_reversion_signals_handle_non_finite_spread_values() -> None:
    spread = pd.Series([0.0, 0.1, -0.1, 0.0, 0.2, -0.2, float("inf"), 0.1, -0.1])
    report = mean_reversion_signals(spread, lookback=3)

    assert pd.isna(report.loc[6, "spread"])
    assert report.loc[6, "signal"] == 0
    assert report.loc[6, "position"] in {-1, 0, 1}


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"lookback": 1}, "lookback"),
        ({"entry_z": 0.0}, "entry_z"),
        ({"entry_z": float("inf")}, "entry_z"),
        ({"entry_z": 1.0, "exit_z": 1.0}, "exit_z"),
        ({"exit_z": -0.1}, "exit_z"),
    ],
)
def test_mean_reversion_signals_validate_parameters(
    kwargs: dict[str, float | int],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        mean_reversion_signals(pd.Series(np.arange(10, dtype=float)), **kwargs)
