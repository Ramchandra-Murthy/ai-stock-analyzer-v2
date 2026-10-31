import numpy as np
import pandas as pd
import pytest

from algorithmic_trading.concentration import (
    concentration_report,
    effective_holdings,
    group_by_sector,
    herfindahl,
)

SECTORS = {"A": "Banks", "B": "Banks", "C": "IT services", "D": "IT services", "E": None}


def _returns(vols, n=500, seed=1):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {name: rng.normal(0.0005, vol, n) for name, vol in vols.items()},
        index=pd.bdate_range("2022-01-03", periods=n),
    )


def test_herfindahl_and_effective_holdings():
    assert herfindahl({"A": 1, "B": 1, "C": 1, "D": 1}) == pytest.approx(0.25)
    assert effective_holdings({"A": 1, "B": 1, "C": 1, "D": 1}) == pytest.approx(4.0)
    assert effective_holdings({"A": 1}) == pytest.approx(1.0)
    assert effective_holdings({"A": 97, "B": 1, "C": 1, "D": 1}) < 1.1


def test_weights_are_normalised_first():
    assert herfindahl({"A": 50, "B": 50}) == pytest.approx(0.5)


def test_group_by_sector_sums_and_labels_unmapped():
    out = group_by_sector(pd.Series({"A": 0.3, "B": 0.2, "C": 0.4, "E": 0.1}), SECTORS)
    assert out.to_dict() == pytest.approx({"IT services": 0.4, "Banks": 0.5, "Unmapped": 0.1})
    assert list(out.index)[0] == "Banks"  # largest first


def test_risk_share_can_differ_from_weight_share():
    rets = _returns({"A": 0.01, "B": 0.01, "C": 0.01, "D": 0.06})
    report = concentration_report(rets, {"A": 25, "B": 25, "C": 25, "D": 25}, SECTORS)
    assert report.weights["D"] == pytest.approx(0.25)
    assert report.risk_share.index[0] == "D" and report.risk_share["D"] > 0.8
    assert report.risk_share.sum() == pytest.approx(1.0)
    assert any("carry" in f and "risk" in f for f in report.flags)


def test_sector_and_stock_limits_are_flagged():
    rets = _returns({"A": 0.01, "B": 0.01, "C": 0.01, "D": 0.01})
    report = concentration_report(rets, {"A": 40, "B": 30, "C": 20, "D": 10}, SECTORS)
    text = " ".join(report.flags)
    assert "Banks is 70%" in text and "A is 40%" in text


def test_balanced_portfolio_has_no_flags():
    rets = _returns(dict.fromkeys("ABCDEFGH", 0.01))
    sectors = {n: f"S{i % 4}" for i, n in enumerate("ABCDEFGH")}
    report = concentration_report(rets, dict.fromkeys("ABCDEFGH", 1), sectors)
    assert report.flags == []
    assert report.effective_holdings == pytest.approx(8.0)


def test_unmapped_capital_is_disclosed_but_not_called_a_sector_breach():
    rets = _returns({"A": 0.01, "B": 0.01, "E": 0.01})
    report = concentration_report(rets, {"A": 10, "B": 10, "E": 80}, SECTORS)
    text = " ".join(report.flags)
    assert "no sector" in text and "Unmapped is" not in text


def test_needs_two_holdings():
    with pytest.raises(ValueError):
        concentration_report(_returns({"A": 0.01}), {"A": 1}, SECTORS)
