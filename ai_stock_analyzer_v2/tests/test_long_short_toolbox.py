import numpy as np
import pandas as pd
import pytest

from engine.long_short_toolbox import (
    big_small_bet_ratio,
    concentration,
    exchange_exposure,
    gross_exposure,
    long_short_counts,
    long_short_toolbox_report,
    market_value,
    net_asset_value,
    net_beta_exposure,
    net_exposure,
    risk_appetite,
    sector_exposure,
)


def sample_market_values():
    return pd.DataFrame(
        {
            "A": [100.0, 120.0],
            "B": [-50.0, -80.0],
            "C": [25.0, 0.0],
            "D": [-25.0, -20.0],
        },
        index=pd.RangeIndex(2),
    )


def test_market_value_and_nav():
    positions = pd.DataFrame({"A": [2, -1]})
    prices = pd.DataFrame({"A": [50, 60]})
    values = market_value(positions, prices)
    assert values["A"].tolist() == [100, -60]

    nav = net_asset_value(pd.DataFrame({"A": [100, -60]}), pd.Series([50, 100]))
    assert nav.tolist() == [150, 40]


def test_gross_net_and_beta_exposure():
    values = sample_market_values()
    nav = pd.Series([50.0, 100.0])
    beta = pd.Series({"A": 1.0, "B": 2.0, "C": 0.5, "D": 1.5})

    assert gross_exposure(values, nav).tolist() == pytest.approx([4.0, 2.2])
    assert net_exposure(values, nav).tolist() == pytest.approx([1.0, 0.2])
    assert net_beta_exposure(values, beta, nav).tolist() == pytest.approx([-0.5, -0.7])


def test_risk_appetite_scales_and_respects_bounds():
    equity = pd.Series([100, 100, 95, 90, 100], dtype=float)
    appetite = risk_appetite(
        equity,
        max_drawdown_tolerance=-0.10,
        min_risk=0.5,
        max_risk=1.0,
        smoothing_span=2,
    )
    assert appetite.between(0.5, 1.0).all()
    assert appetite.iloc[-1] > appetite.iloc[2]


def test_concentration_counts_positions():
    values = sample_market_values()
    assert concentration(values).tolist() == [4, 3]
    counts = long_short_counts(values)
    assert counts.iloc[0].to_dict() == {"long_count": 2, "short_count": 2}
    assert counts.iloc[1].to_dict() == {"long_count": 1, "short_count": 2}


def test_big_small_bet_ratio():
    values = sample_market_values()
    assert big_small_bet_ratio(values).tolist() == pytest.approx([4.0, 6.0])


def test_exchange_and_sector_exposure():
    values = sample_market_values()
    nav = pd.Series([50.0, 100.0])
    groups = pd.Series({"A": "NSE", "B": "NSE", "C": "BSE", "D": "BSE"})
    exchange = exchange_exposure(values, groups, nav)
    assert exchange.loc[0, "NSE"] == pytest.approx(1.0)
    assert exchange.loc[0, "BSE"] == pytest.approx(0.0)

    sectors = pd.Series({"A": "Tech", "B": "Finance", "C": "Tech", "D": "Finance"})
    sector = sector_exposure(values, sectors, nav)
    assert sector.loc[0, "Tech"] == pytest.approx(2.5)
    assert sector.loc[0, "Finance"] == pytest.approx(-1.5)


def test_report_contains_core_metrics():
    values = sample_market_values()
    report = long_short_toolbox_report(
        values,
        pd.Series([50.0, 100.0]),
        pd.Series({"A": 1.0, "B": 2.0, "C": 0.5, "D": 1.5}),
    )
    assert set(report) == {
        "gross_exposure",
        "net_exposure",
        "net_beta_exposure",
        "concentration",
        "big_small_bet_ratio",
        "long_count",
        "short_count",
    }


def test_invalid_inputs_raise():
    values = sample_market_values()
    with pytest.raises(ValueError):
        gross_exposure(values, 0)
    with pytest.raises(ValueError):
        risk_appetite([100, 95], 0.05, 0.5, 1.0)
    with pytest.raises(ValueError):
        risk_appetite([100, 95], -0.05, 1.0, 0.5)
    with pytest.raises(ValueError):
        risk_appetite([100, 95], -0.05, 0.5, 1.0, curve_shape="bad")


def test_risk_appetite_drawdown_window_and_empty_series():
    result = risk_appetite(
        np.array([100.0, 98.0, 101.0]),
        max_drawdown_tolerance=-0.05,
        min_risk=0.5,
        max_risk=1.0,
        drawdown_window=2,
    )
    assert len(result) == 3
    empty = risk_appetite([], -0.05, 0.5, 1.0)
    assert empty.empty
