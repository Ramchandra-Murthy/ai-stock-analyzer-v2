import numpy as np
import pandas as pd
import pytest

from mutual_funds import analytics as mf
from mutual_funds import nav as mn


def _nav(years=6, drift=0.0005, vol=0.008, seed=0, start="2018-01-01"):
    n = int(years * 252)
    r = np.random.default_rng(seed).normal(drift, vol, n)
    idx = pd.bdate_range(start, periods=n)
    return pd.Series(100 * np.cumprod(1 + r), index=idx, name="fund")


# ---- parsing --------------------------------------------------------------------------
def test_parse_response_sorts_dedupes_and_drops_bad_rows():
    payload = {
        "meta": {"scheme_name": "X Direct Growth", "scheme_code": 1},
        "data": [
            {"date": "03-01-2024", "nav": "12.5"},
            {"date": "01-01-2024", "nav": "10"},
            {"date": "02-01-2024", "nav": "N.A."},
            {"date": "bad", "nav": "5"},
            {"date": "03-01-2024", "nav": "12.6"},
            {"date": "04-01-2024", "nav": "0"},
        ],
    }
    meta, s = mn.parse_nav_response(payload)
    assert s.index.tolist() == [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-03")]
    assert s.tolist() == [10.0, 12.6] and meta["scheme_code"] == 1 and s.name == "X Direct Growth"


@pytest.mark.parametrize(
    "bad",
    [None, {}, {"data": []}, {"data": [{"d": 1}]}, {"data": [{"date": "01-01-2024", "nav": "1"}]}],
)
def test_parse_rejects_bad_payloads(bad):
    with pytest.raises(ValueError):
        mn.parse_nav_response(bad)


def test_fetch_and_search_use_injected_fetcher_and_validate_inputs():
    seen = []
    payload = {
        "meta": {},
        "data": [{"date": "01-01-2024", "nav": "1"}, {"date": "02-01-2024", "nav": "2"}],
    }

    def fetch(url):
        seen.append(url)
        return (
            payload
            if "/mf/118" in url
            else [{"schemeCode": 1, "schemeName": "A"}, {"schemeCode": 2, "schemeName": "B"}]
        )

    mn.fetch_scheme("118834", fetch)
    assert seen[-1].endswith("/mf/118834")
    assert (
        len(mn.search_schemes("mirae fund", fetch, limit=1)) == 1 and "q=mirae%20fund" in seen[-1]
    )
    for bad in ("12;rm", "abc", ""):
        with pytest.raises(ValueError):
            mn.fetch_scheme(bad, fetch)
    with pytest.raises(ValueError):
        mn.search_schemes("ab", fetch)
    with pytest.raises(ValueError):
        mn.default_fetch("https://evil.example.com/x")


def test_direct_growth_detection():
    assert mn.is_direct_growth("Mirae Large & Midcap Fund - Direct Plan - Growth")
    assert not mn.is_direct_growth("X - Direct Plan - IDCW") and not mn.is_direct_growth(
        "X - Regular - Growth"
    )


# ---- returns --------------------------------------------------------------------------
def test_trailing_returns_hand_computed():
    idx = pd.to_datetime(["2023-10-20", "2025-10-20", "2026-04-20", "2026-10-20"])
    s = pd.Series([100.0, 121.0, 110.0, 133.1], index=idx)
    t = mf.trailing_returns(s)
    assert t.loc["6M", "Return"] == pytest.approx(133.1 / 110 - 1)
    assert t.loc["1Y", "Return"] == pytest.approx(133.1 / 121 - 1) or "1Y" not in t.index
    assert t.loc["3Y", "Return"] == pytest.approx((133.1 / 100) ** (1 / 3) - 1)
    assert "5Y" not in t.index and t.loc["3Y", "Type"] == "CAGR"


def test_rolling_returns_and_summary():
    s = _nav(6)
    r = mf.rolling_returns(s, 3)
    assert r.index[0] >= s.index[0] + pd.DateOffset(years=3)
    summary = mf.rolling_summary(r)
    assert (
        summary["min"] <= summary["median"] <= summary["max"]
        and 0 <= summary["share_negative"] <= 1
    )
    with pytest.raises(ValueError):
        mf.rolling_returns(_nav(2), 3)


def test_unsorted_or_invalid_nav_rejected():
    with pytest.raises(ValueError):
        mf.trailing_returns(
            pd.Series([1.0, 2.0], index=pd.to_datetime(["2024-02-01", "2024-01-01"]))
        )
    with pytest.raises(ValueError):
        mf.trailing_returns(
            pd.Series([1.0, -2.0], index=pd.to_datetime(["2024-01-01", "2024-02-01"]))
        )


# ---- xirr / sip / swp -----------------------------------------------------------------
def test_xirr_known_values():
    d0 = pd.Timestamp("2024-01-01")
    assert mf.xirr([(d0, -1000), (d0 + pd.Timedelta(days=365), 1100)]) == pytest.approx(
        0.10, abs=1e-6
    )
    assert mf.xirr([(d0, -1000), (d0 + pd.Timedelta(days=730), 1210)]) == pytest.approx(
        0.10, abs=1e-6
    )
    assert mf.xirr([(d0, -1000), (d0 + pd.Timedelta(days=365), 800)]) == pytest.approx(
        -0.20, abs=1e-6
    )
    for bad in ([(d0, -1)], [(d0, -1), (d0, -2)]):
        with pytest.raises(ValueError):
            mf.xirr(bad)


def test_sip_on_flat_and_growing_nav():
    idx = pd.bdate_range("2022-01-03", "2024-12-31")
    flat = pd.Series(10.0, index=idx)
    res = mf.sip_simulation(flat, 1000)
    assert res["final_value"] == pytest.approx(res["invested"]) and res["xirr"] == pytest.approx(
        0, abs=1e-6
    )
    assert res["invested"] == pytest.approx(1000 * len(res["ledger"]))
    grow = pd.Series(10.0 * 1.0003 ** np.arange(len(idx)), index=idx)
    g = mf.sip_simulation(grow, 1000)
    assert g["final_value"] > g["invested"] and g["xirr"] > 0.05


def test_sip_step_up_increases_amounts_yearly():
    idx = pd.bdate_range("2021-01-04", "2024-06-28")
    res = mf.sip_simulation(pd.Series(10.0, index=idx), 1000, step_up=0.10)
    amounts = res["ledger"]["amount"]
    assert (
        amounts.iloc[0] == 1000
        and amounts.iloc[12] == pytest.approx(1100)
        and amounts.iloc[24] == pytest.approx(1210)
    )
    with pytest.raises(ValueError):
        mf.sip_simulation(
            pd.Series([1.0, 2.0], index=pd.to_datetime(["2024-01-01", "2024-01-02"])), 1000
        )
    with pytest.raises(ValueError):
        mf.sip_simulation(_nav(), -5)


def test_lumpsum():
    s = pd.Series([100.0, 150.0], index=pd.to_datetime(["2020-01-01", "2022-01-01"]))
    r = mf.lumpsum_value(s, 10_000)
    assert r["final_value"] == pytest.approx(15_000) and r["cagr"] == pytest.approx(
        1.5 ** (1 / 2) - 1, abs=2e-3
    )


def test_swp_runs_out_on_flat_nav_and_lasts_on_growth():
    idx = pd.bdate_range("2020-01-01", "2023-12-29")
    flat = mf.swp_simulation(pd.Series(10.0, index=idx), 100_000, 10_000)
    assert flat["depleted_on"] is not None and flat["total_withdrawn"] == pytest.approx(100_000)
    grow = pd.Series(10.0 * 1.0006 ** np.arange(len(idx)), index=idx)
    ok = mf.swp_simulation(grow, 100_000, 1_000)
    assert ok["depleted_on"] is None and ok["remaining_value"] > 0
    assert ok["total_withdrawn"] + ok["remaining_value"] > 100_000


def test_sip_future_value_and_required_sip_roundtrip():
    r_m = 1.12 ** (1 / 12) - 1
    expected = 5000 * (((1 + r_m) ** 120 - 1) / r_m)  # ordinary annuity, 10 years
    assert mf.sip_future_value(5000, 10, 0.12) == pytest.approx(expected)
    sip = mf.required_sip(10_000_000, 15, 0.12, step_up=0.10)
    assert mf.sip_future_value(sip, 15, 0.12, 0.10) == pytest.approx(10_000_000)
    assert mf.required_sip(10_000_000, 15, 0.12, 0.10) < mf.required_sip(10_000_000, 15, 0.12, 0.0)
    with pytest.raises(ValueError):
        mf.required_sip(-1, 5, 0.1)


def test_ter_drag():
    r = mf.ter_drag(10, 0.12, 0.015, 0.005)
    assert r["difference"] == pytest.approx(100_000 * (1.115**10 - 1.105**10))
    with pytest.raises(ValueError):
        mf.ter_drag(10, 0.12, 0.005, 0.015)


# ---- risk -----------------------------------------------------------------------------
def test_risk_metrics_properties_and_drawdown_hand_case():
    s = _nav(5, seed=2)
    m = mf.risk_metrics(s)
    assert 0 < m["volatility"] < 0.5 and m["max_drawdown"] < 0 and m["drawdown_days"] >= 0
    idx = pd.bdate_range("2024-01-01", periods=300)
    v = np.r_[np.linspace(100, 120, 100), np.linspace(120, 90, 50), np.linspace(90, 130, 150)]
    h = mf.risk_metrics(pd.Series(v, index=idx))
    assert h["max_drawdown"] == pytest.approx(90 / 120 - 1, abs=0.01) and h["recovery_days"] > 0
    with pytest.raises(ValueError):
        mf.risk_metrics(s.iloc[:30])


def test_capture_and_beta_recover_a_levered_benchmark():
    bench = _nav(8, drift=0.0004, vol=0.01, seed=3)
    daily = bench.pct_change().fillna(0)
    fund = (1 + 1.2 * daily).cumprod() * 100
    c = mf.capture_and_beta(fund, bench)
    assert c["beta"] == pytest.approx(1.2, abs=0.05) and c["correlation"] > 0.98
    assert c["up_capture"] > 1.0 and c["down_capture"] > 1.0
    with pytest.raises(ValueError):
        mf.capture_and_beta(bench.iloc[:200], bench.iloc[:200])


def test_compare_funds_sorted_and_validated():
    t = mf.compare_funds({"A": _nav(4, seed=1), "B": _nav(4, drift=0.0001, seed=2)})
    assert set(t.index) == {"A", "B"} and t["Sharpe"].is_monotonic_decreasing
    with pytest.raises(ValueError):
        mf.compare_funds({"A": _nav(0.2), "B": _nav(0.2, seed=1)})


def test_benchmark_with_timezone_overlaps_naive_nav():
    import numpy as np

    from mutual_funds.analytics import capture_and_beta

    idx = pd.bdate_range("2018-01-01", "2024-12-31")
    rng = np.random.default_rng(1)
    fund = pd.Series(100 * np.cumprod(1 + rng.normal(5e-4, 0.01, len(idx))), index=idx)
    bench = pd.Series(
        1e4 * np.cumprod(1 + rng.normal(5e-4, 0.01, len(idx))),
        index=idx.tz_localize("Asia/Kolkata"),
    )
    assert capture_and_beta(fund, bench)["months"] > 60


def test_default_fetch_retries_then_reports(monkeypatch):
    import urllib.request

    from mutual_funds import nav as nav_module

    calls = []

    def boom(*_a, **_k):
        calls.append(1)
        raise OSError("down")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    with pytest.raises(ConnectionError):
        nav_module.default_fetch(nav_module.BASE_URL + "/mf/1", attempts=3, pause=0)
    assert len(calls) == 3
