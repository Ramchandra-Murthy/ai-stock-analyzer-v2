import numpy as np
import pandas as pd
import pytest

from algorithmic_trading import sector_rotation as rs


def _px(drift, n=400, seed=0, vol=0.004):
    r = np.random.default_rng(seed).normal(drift, vol, n)
    return pd.Series(100 * np.exp(np.cumsum(r)), index=pd.bdate_range("2022-01-03", periods=n))


def test_ratio_rebased_and_validated():
    a = pd.Series([10.0, 11, 12])
    b = pd.Series([10.0, 10, 10])
    assert rs.relative_strength_ratio(a, b).tolist() == pytest.approx([100, 110, 120])
    with pytest.raises(ValueError):
        rs.relative_strength_ratio(pd.Series([1.0]), pd.Series([1.0]))
    with pytest.raises(ValueError):
        rs.relative_strength_ratio(pd.Series([1.0, -1]), pd.Series([1.0, 1]))


def test_quadrants_cover_all_four_cases():
    assert rs.quadrant(101, 101) == "Leading"
    assert rs.quadrant(101, 99) == "Weakening"
    assert rs.quadrant(99, 99) == "Lagging"
    assert rs.quadrant(99, 101) == "Improving"


def test_outperformer_leads_and_underperformer_lags():
    bench = _px(0.0003, seed=1)
    up = bench * np.exp(np.linspace(0, 0.6, len(bench)))
    down = bench * np.exp(np.linspace(0, -0.6, len(bench)))
    table = rs.sector_table(pd.DataFrame({"UP": up, "DOWN": down}), bench)
    assert table.loc["UP", "Quadrant"] == "Leading" and table.loc["DOWN", "Quadrant"] == "Lagging"
    assert (
        table.index[0] == "UP"
        and table.loc["UP", "63d vs index"] > 0 > table.loc["DOWN", "63d vs index"]
    )


def test_rrg_point_is_causal():
    bench, sector = _px(0.0003, seed=2), _px(0.0006, seed=3)
    full = rs.relative_strength_ratio(sector, bench)
    cut = 300
    assert rs.rrg_point(full.iloc[:cut]) == rs.rrg_point(
        rs.relative_strength_ratio(sector.iloc[:cut], bench.iloc[:cut])
    )


def test_insufficient_history():
    bench = _px(0, n=40)
    with pytest.raises(ValueError):
        rs.sector_table(pd.DataFrame({"A": bench}), bench)
    with pytest.raises(ValueError):
        rs.rrg_point(rs.relative_strength_ratio(bench, bench))
