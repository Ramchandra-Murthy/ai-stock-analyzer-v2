import pandas as pd
import pytest

from algorithmic_trading.portfolio_risk import (
    dynamic_risk_appetite,
    gross_exposure,
    market_value,
    net_asset_value,
    net_beta_exposure,
    net_exposure,
)


def test_market_value_and_nav() -> None:
    positions = pd.Series([10, -5], index=["A", "B"])
    prices = pd.Series([100, 200], index=["A", "B"])
    values = market_value(positions, prices)
    frame = pd.DataFrame([values.values], columns=values.index)
    nav = net_asset_value(frame, pd.Series([1_000]))
    assert values["A"] == 1_000
    assert values["B"] == -1_000
    assert nav.iloc[0] == 1_000


def test_exposure_metrics() -> None:
    values = pd.DataFrame(
        [[60_000, -40_000]],
        columns=["LONG", "SHORT"],
    )
    nav = pd.Series([100_000])
    beta = pd.Series([1.2, 0.8], index=values.columns)

    assert gross_exposure(values, nav).iloc[0] == pytest.approx(1.0)
    assert net_exposure(values, nav).iloc[0] == pytest.approx(0.2)
    assert net_beta_exposure(values, beta, nav).iloc[0] == pytest.approx(0.4)


def test_dynamic_risk_appetite_is_bounded() -> None:
    equity = pd.Series([100, 105, 95, 90, 100], dtype=float)
    result = dynamic_risk_appetite(
        equity,
        max_drawdown_tolerance=-0.20,
        min_risk=0.02,
        max_risk=0.10,
    )
    assert (result >= 0.02).all()
    assert (result <= 0.10).all()


def test_dynamic_risk_validation() -> None:
    with pytest.raises(ValueError, match="max_drawdown"):
        dynamic_risk_appetite(
            pd.Series([100, 90]),
            max_drawdown_tolerance=0.20,
            min_risk=0.02,
            max_risk=0.10,
        )
