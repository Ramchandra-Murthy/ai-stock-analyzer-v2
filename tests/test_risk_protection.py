import pandas as pd
import pytest

from algorithmic_trading.risk_protection import apply_close_stop


def test_close_stop_exits_on_next_bar_signal_after_threshold_breach() -> None:
    index = pd.date_range("2026-01-01", periods=5, freq="D")
    prices = pd.Series([100.0, 100.0, 94.0, 90.0, 92.0], index=index)
    signals = pd.Series([1.0, 1.0, 1.0, 1.0, 0.0], index=index)

    protected = apply_close_stop(prices, signals, stop_loss_fraction=0.05)

    assert protected.iloc[0] == 1.0
    assert protected.iloc[1] == 1.0
    assert protected.iloc[2] == 0.0
    assert protected.iloc[3] == 0.0


def test_close_stop_supports_short_positions() -> None:
    index = pd.date_range("2026-01-01", periods=4, freq="D")
    prices = pd.Series([100.0, 100.0, 106.0, 107.0], index=index)
    signals = pd.Series([-1.0, -1.0, -1.0, 0.0], index=index)

    protected = apply_close_stop(prices, signals, stop_loss_fraction=0.05)

    assert protected.iloc[2] == 0.0
    assert protected.iloc[3] == 0.0


def test_close_stop_does_not_reenter_until_original_signal_is_flat() -> None:
    index = pd.date_range("2026-01-01", periods=6, freq="D")
    prices = pd.Series([100.0, 100.0, 94.0, 95.0, 96.0, 97.0], index=index)
    signals = pd.Series([1.0, 1.0, 1.0, 1.0, 0.0, 1.0], index=index)

    protected = apply_close_stop(prices, signals, stop_loss_fraction=0.05)

    assert protected.iloc[2] == 0.0
    assert protected.iloc[3] == 0.0
    assert protected.iloc[4] == 0.0
    assert protected.iloc[5] == 1.0


def test_close_stop_rejects_invalid_inputs() -> None:
    index = pd.date_range("2026-01-01", periods=2, freq="D")
    prices = pd.Series([100.0, 101.0], index=index)
    signals = pd.Series([1.0, 0.0], index=index)

    for invalid_stop in (0.0, 1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="stop_loss_fraction"):
            apply_close_stop(prices, signals, invalid_stop)

    with pytest.raises(ValueError, match="prices must be finite"):
        apply_close_stop(
            pd.Series([100.0, float("inf")], index=index),
            signals,
            0.05,
        )


def test_close_stop_treats_near_zero_signal_as_flat() -> None:
    index = pd.date_range("2026-01-01", periods=6, freq="D")
    prices = pd.Series([100.0, 100.0, 94.0, 95.0, 96.0, 97.0], index=index)
    signals = pd.Series([1.0, 1.0, 1.0, 1.0, 1e-15, 1.0], index=index)

    protected = apply_close_stop(prices, signals, stop_loss_fraction=0.05)

    assert protected.iloc[2] == 0.0
    assert protected.iloc[3] == 0.0
    assert protected.iloc[4] == 0.0
    assert protected.iloc[5] == 1.0
