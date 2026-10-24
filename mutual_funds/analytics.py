"""Mutual-fund return, SIP/SWP, risk and comparison analytics (research only)."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252
PERIODS = {"1M": 1, "3M": 3, "6M": 6, "1Y": 12, "3Y": 36, "5Y": 60, "10Y": 120}


def _check(nav: pd.Series) -> pd.Series:
    s = pd.to_numeric(nav, errors="coerce").dropna()
    if len(s) < 2 or (s <= 0).any() or not s.index.is_monotonic_increasing:
        raise ValueError("NAV must be a sorted series of at least two positive values.")
    return s


def _asof(nav: pd.Series, when: pd.Timestamp) -> float | None:
    """NAV on or before ``when`` (None if before the first observation)."""
    pos = nav.index.searchsorted(when, side="right") - 1
    return None if pos < 0 else float(nav.iloc[pos])


def trailing_returns(nav: pd.Series) -> pd.DataFrame:
    """Absolute (<=1Y) or annualised (>1Y) trailing returns, plus since inception."""
    s = _check(nav)
    end = s.index[-1]
    rows = []
    for label, months in PERIODS.items():
        start = end - pd.DateOffset(months=months)
        if start < s.index[0]:
            continue
        base = _asof(s, start)
        if base is None:
            continue
        total = float(s.iloc[-1] / base - 1.0)
        years = months / 12.0
        rows.append(
            {
                "Period": label,
                "Return": total if months <= 12 else (1 + total) ** (1 / years) - 1,
                "Type": "absolute" if months <= 12 else "CAGR",
            }
        )
    days = (end - s.index[0]).days
    total = float(s.iloc[-1] / s.iloc[0] - 1.0)
    rows.append(
        {
            "Period": "Since start",
            "Return": total if days <= 365 else (1 + total) ** (365.25 / days) - 1,
            "Type": "absolute" if days <= 365 else "CAGR",
        }
    )
    return pd.DataFrame(rows).set_index("Period")


def rolling_returns(nav: pd.Series, years: int = 3) -> pd.Series:
    """Annualised return over every ``years``-year window ending on each date (point in time)."""
    s = _check(nav)
    if years < 1:
        raise ValueError("years must be at least 1")
    out = {}
    for date in s.index:
        start = date - pd.DateOffset(years=years)
        if start < s.index[0]:
            continue
        base = _asof(s, start)
        out[date] = (s.loc[date] / base) ** (1.0 / years) - 1.0
    if not out:
        raise ValueError(f"History is shorter than {years} years.")
    return pd.Series(out)


def rolling_summary(rolling: pd.Series) -> dict[str, float]:
    return {
        "min": float(rolling.min()),
        "median": float(rolling.median()),
        "max": float(rolling.max()),
        "share_negative": float((rolling < 0).mean()),
        "share_above_12pct": float((rolling > 0.12).mean()),
        "windows": float(len(rolling)),
    }


# ---------------------------------------------------------------- XIRR / SIP / SWP
def xirr(cashflows: list[tuple[pd.Timestamp, float]]) -> float:
    """Annualised internal rate of return for dated cash flows (negative = invested)."""
    if len(cashflows) < 2:
        raise ValueError("Need at least two cash flows.")
    amounts = np.array([c for _, c in cashflows], dtype=float)
    if not ((amounts > 0).any() and (amounts < 0).any()):
        raise ValueError("Cash flows need both outflows and inflows.")
    t0 = min(d for d, _ in cashflows)
    years = np.array([(d - t0).days / 365.0 for d, _ in cashflows])

    def npv(rate: float) -> float:
        return float(np.sum(amounts / (1.0 + rate) ** years))

    lo, hi = -0.9999, 10.0
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        raise ValueError("XIRR could not be bracketed for these cash flows.")
    for _ in range(200):
        mid = (lo + hi) / 2.0
        f_mid = npv(mid)
        if abs(f_mid) < 1e-9:
            return mid
        if f_lo * f_mid < 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2.0


def sip_simulation(
    nav: pd.Series, monthly: float, *, step_up: float = 0.0, day: int = 5
) -> dict[str, object]:
    """Invest ``monthly`` on the first NAV on/after ``day`` of each month, optional yearly step-up.

    Returns invested, final value, XIRR, units and the monthly ledger. Ignores exit load and
    taxes. The last NAV is treated as the redemption value.
    """
    s = _check(nav)
    if monthly <= 0 or not 0 <= step_up <= 1 or not 1 <= day <= 28:
        raise ValueError("monthly must be positive, step_up in [0, 1], day in 1..28")
    months = pd.period_range(s.index[0], s.index[-1], freq="M")
    rows, flows, units, invested = [], [], 0.0, 0.0
    first_month = months[0]
    for p in months:
        target = pd.Timestamp(year=p.year, month=p.month, day=day)
        pos = s.index.searchsorted(target, side="left")
        if pos >= len(s) or s.index[pos].to_period("M") != p or s.index[pos] == s.index[-1]:
            continue
        date, price = s.index[pos], float(s.iloc[pos])
        amount = monthly * (1.0 + step_up) ** ((p - first_month).n // 12)
        units += amount / price
        invested += amount
        flows.append((date, -amount))
        rows.append(
            {
                "date": date,
                "amount": amount,
                "nav": price,
                "units": units,
                "invested": invested,
                "value": units * price,
            }
        )
    if len(rows) < 2:
        raise ValueError("History is too short for a SIP simulation.")
    final = units * float(s.iloc[-1])
    flows.append((s.index[-1], final))
    return {
        "invested": invested,
        "final_value": final,
        "xirr": xirr(flows),
        "units": units,
        "gain": final - invested,
        "ledger": pd.DataFrame(rows).set_index("date"),
    }


def lumpsum_value(nav: pd.Series, amount: float) -> dict[str, float]:
    s = _check(nav)
    if amount <= 0:
        raise ValueError("amount must be positive")
    final = amount * float(s.iloc[-1] / s.iloc[0])
    days = (s.index[-1] - s.index[0]).days
    return {
        "final_value": final,
        "cagr": (final / amount) ** (365.25 / days) - 1 if days > 0 else 0.0,
    }


def swp_simulation(
    nav: pd.Series, corpus: float, monthly_withdrawal: float, day: int = 5
) -> dict[str, object]:
    """Withdraw a fixed amount monthly by redeeming units; reports when the corpus runs out."""
    s = _check(nav)
    if corpus <= 0 or monthly_withdrawal <= 0 or not 1 <= day <= 28:
        raise ValueError("corpus and withdrawal must be positive; day in 1..28")
    units = corpus / float(s.iloc[0])
    withdrawn, depleted_on = 0.0, None
    rows = []
    for p in pd.period_range(s.index[0], s.index[-1], freq="M")[1:]:
        pos = s.index.searchsorted(pd.Timestamp(year=p.year, month=p.month, day=day), side="left")
        if pos >= len(s) or s.index[pos].to_period("M") != p:
            continue
        price = float(s.iloc[pos])
        need = min(monthly_withdrawal / price, units)
        units -= need
        withdrawn += need * price
        rows.append(
            {"date": s.index[pos], "withdrawn": need * price, "remaining_value": units * price}
        )
        if units <= 1e-9:
            depleted_on = s.index[pos]
            break
    return {
        "total_withdrawn": withdrawn,
        "remaining_value": units * float(s.iloc[-1]) if depleted_on is None else 0.0,
        "depleted_on": depleted_on,
        "ledger": pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame(),
    }


def sip_future_value(
    monthly: float, years: float, annual_return: float, step_up: float = 0.0
) -> float:
    """Future value of an end-of-month SIP at a constant return, stepping up each year."""
    if monthly <= 0 or years <= 0 or annual_return <= -1 or not 0 <= step_up <= 1:
        raise ValueError("monthly and years must be positive, return > -100%, step_up in [0, 1]")
    r = (1.0 + annual_return) ** (1 / 12.0) - 1.0
    total, n = 0.0, int(round(years * 12))
    for m in range(1, n + 1):
        amount = monthly * (1.0 + step_up) ** ((m - 1) // 12)
        total += amount * (1.0 + r) ** (n - m)
    return total


def required_sip(target: float, years: float, annual_return: float, step_up: float = 0.0) -> float:
    """Monthly SIP needed to reach ``target`` (the future value is linear in the SIP amount)."""
    if target <= 0:
        raise ValueError("target must be positive")
    return target / sip_future_value(1.0, years, annual_return, step_up)


def ter_drag(
    years: float,
    gross_return: float,
    ter_regular: float,
    ter_direct: float,
    amount: float = 100_000.0,
) -> dict[str, float]:
    """Corpus difference between a regular and a direct plan that earn the same gross return."""
    if years <= 0 or amount <= 0 or ter_regular < ter_direct or ter_direct < 0:
        raise ValueError("years, amount > 0 and 0 <= ter_direct <= ter_regular required")
    direct = amount * (1 + gross_return - ter_direct) ** years
    regular = amount * (1 + gross_return - ter_regular) ** years
    return {"direct": direct, "regular": regular, "difference": direct - regular}


# ---------------------------------------------------------------- risk
def daily_returns(nav: pd.Series) -> pd.Series:
    return _check(nav).pct_change().dropna()


def monthly_returns(nav: pd.Series) -> pd.Series:
    return _check(nav).resample("ME").last().pct_change().dropna()


def risk_metrics(nav: pd.Series, risk_free: float = 0.065) -> dict[str, float]:
    """Annual volatility, Sharpe, Sortino, max drawdown and its recovery. ``risk_free`` is annual."""
    s = _check(nav)
    r = s.pct_change().dropna()
    if len(r) < 60:
        raise ValueError("At least 60 NAV returns are needed.")
    ann_ret = float(
        (s.iloc[-1] / s.iloc[0]) ** (365.25 / max((s.index[-1] - s.index[0]).days, 1)) - 1
    )
    vol = float(r.std(ddof=1) * np.sqrt(TRADING_DAYS))
    rf_d = (1 + risk_free) ** (1 / TRADING_DAYS) - 1
    excess = r - rf_d
    downside = np.sqrt(np.mean(np.minimum(excess, 0.0) ** 2)) * np.sqrt(TRADING_DAYS)
    dd = s / s.cummax() - 1.0
    trough = dd.idxmin()
    peak = s.loc[:trough].idxmax()
    recovered = s.loc[trough:][s.loc[trough:] >= s.loc[peak]]
    return {
        "cagr": ann_ret,
        "volatility": vol,
        "sharpe": float(excess.mean() * TRADING_DAYS / vol) if vol > 1e-12 else 0.0,
        "sortino": float(excess.mean() * TRADING_DAYS / downside) if downside > 1e-12 else 0.0,
        "max_drawdown": float(dd.min()),
        "drawdown_days": float((trough - peak).days),
        "recovery_days": (
            float((recovered.index[0] - trough).days) if len(recovered) else float("nan")
        ),
    }


def capture_and_beta(
    fund: pd.Series, benchmark: pd.Series, risk_free: float = 0.065
) -> dict[str, float]:
    """Up/down capture, beta and Jensen alpha on monthly returns versus a benchmark."""
    f, b = monthly_returns(fund), monthly_returns(benchmark)
    both = pd.concat([f, b], axis=1, join="inner").dropna()
    both.columns = ["fund", "bench"]
    if len(both) < 24:
        raise ValueError("At least 24 overlapping months are needed.")
    up, down = both[both.bench > 0], both[both.bench < 0]

    def geo(x: pd.Series) -> float:
        return float((1 + x).prod() ** (12 / len(x)) - 1)

    rf_m = (1 + risk_free) ** (1 / 12) - 1
    ex_f, ex_b = both.fund - rf_m, both.bench - rf_m
    beta = float(np.cov(ex_f, ex_b, ddof=1)[0, 1] / ex_b.var(ddof=1))
    return {
        "up_capture": (
            geo(up.fund) / geo(up.bench) if len(up) >= 6 and geo(up.bench) != 0 else float("nan")
        ),
        "down_capture": (
            geo(down.fund) / geo(down.bench)
            if len(down) >= 6 and geo(down.bench) != 0
            else float("nan")
        ),
        "beta": beta,
        "alpha_annual": float((ex_f.mean() - beta * ex_b.mean()) * 12),
        "correlation": float(both.fund.corr(both.bench)),
        "months": float(len(both)),
    }


def compare_funds(navs: dict[str, pd.Series], risk_free: float = 0.065) -> pd.DataFrame:
    """One row per fund over the common date range."""
    frame = pd.concat(navs, axis=1, join="inner").dropna()
    if len(frame) < 100:
        raise ValueError("The funds need at least 100 common NAV dates.")
    rows = {}
    for name in frame.columns:
        m = risk_metrics(frame[name], risk_free)
        rows[name] = {
            "CAGR": m["cagr"],
            "Volatility": m["volatility"],
            "Sharpe": m["sharpe"],
            "Sortino": m["sortino"],
            "Max drawdown": m["max_drawdown"],
        }
    return pd.DataFrame(rows).T.sort_values("Sharpe", ascending=False)
