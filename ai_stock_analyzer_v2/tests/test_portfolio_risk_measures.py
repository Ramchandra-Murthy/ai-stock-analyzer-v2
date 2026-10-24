import numpy as np
import pandas as pd
import pytest

from algorithmic_trading import risk_metrics as rm


def _rets(n=500, seed=1):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        rng.normal(0.0005, 0.01, (n, 3)),
        columns=list("ABC"),
        index=pd.bdate_range("2021-01-01", periods=n),
    )


def test_var_cvar_hand_computed():
    r = pd.Series(np.arange(-50, 50) / 1000.0)  # -5.0% .. +4.9%
    assert rm.historical_var(r, 0.95) == pytest.approx(-np.quantile(r, 0.05))
    # tail = returns <= quantile: the 5 worst days -5.0..-4.6 -> mean -4.8%
    assert rm.historical_cvar(r, 0.95) == pytest.approx(0.048)
    assert rm.historical_cvar(r, 0.95) >= rm.historical_var(r, 0.95)


def test_var_validation():
    with pytest.raises(ValueError):
        rm.historical_var(pd.Series([0.01] * 5))
    with pytest.raises(ValueError):
        rm.historical_var(pd.Series(np.zeros(50)), 0.2)


def test_weights_validation_and_normalisation():
    assert rm.normalise_weights({"A": 2, "B": 2}).tolist() == [0.5, 0.5]
    for bad in ({"A": -1, "B": 2}, {"A": 0}, {}):
        with pytest.raises(ValueError):
            rm.normalise_weights(bad)
    with pytest.raises(ValueError):
        rm.portfolio_returns(_rets(), {"Z": 1})


def test_risk_contributions_sum_to_one_and_match_variance_identity():
    r = _rets()
    w = {"A": 0.5, "B": 0.3, "C": 0.2}
    c = rm.risk_contributions(r, w)
    assert c.sum() == pytest.approx(1.0)
    port = rm.portfolio_returns(r, w)
    # contribution_i * portfolio variance == w_i * cov(asset_i, portfolio)
    for k in "ABC":
        assert c[k] * port.var() == pytest.approx(w[k] * r[k].cov(port))


def test_single_asset_contributes_everything():
    assert rm.risk_contributions(_rets(), {"A": 1.0})["A"] == pytest.approx(1.0)


def test_drawdown_series_hand_computed():
    d = rm.drawdown_series(pd.Series([0.1, -0.1, 0.1]))
    assert d.min() == pytest.approx(-0.1)


def test_breaker_cuts_exposure_after_breach_and_never_amplifies_losses():
    r = pd.Series([0.0] * 5 + [-0.06, -0.06] + [-0.05] * 10 + [0.01] * 30)
    out = rm.breaker_simulation(r, limit=0.10, cooldown=10)
    assert (out["with_breaker"].iloc[7:17] == 0).all()  # flat during cooldown
    assert (1 + out["with_breaker"]).prod() > (1 + out["raw"]).prod()
    assert out.attrs["triggered"]


def test_breaker_is_causal():
    r = _rets(400)["A"]
    full = rm.breaker_simulation(r, 0.05, 10)["with_breaker"]
    cut = rm.breaker_simulation(r.iloc[:250], 0.05, 10)["with_breaker"]
    pd.testing.assert_series_equal(full.iloc[:250], cut)


def test_breaker_validation():
    with pytest.raises(ValueError):
        rm.breaker_simulation(pd.Series([0.0]), limit=0)


def test_summary_keys_and_ordering():
    s = rm.risk_summary(_rets(), {"A": 1, "B": 1, "C": 1})
    assert s["var_99"] >= s["var_95"] and s["cvar_99"] >= s["cvar_95"]
    assert s["max_drawdown"] <= 0
