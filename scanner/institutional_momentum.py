"""Institutional momentum scoring helpers."""

from __future__ import annotations

import math

import pandas as pd


def _bounded(value: float, scale: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return math.tanh(value / scale)


def _latest_net(flow: pd.DataFrame, category: str) -> float:
    if flow is None or flow.empty or "Net Value (₹ Cr)" not in flow.columns:
        return 0.0
    if "Category" in flow.columns:
        mask = flow["Category"].astype(str).str.contains(category, case=False, na=False)
        values = pd.to_numeric(flow.loc[mask, "Net Value (₹ Cr)"], errors="coerce").dropna()
        return float(values.iloc[-1]) if not values.empty else 0.0
    column = "FII Net Value (₹ Cr)" if category == "FII" else "DII Net Value (₹ Cr)"
    if column in flow.columns:
        values = pd.to_numeric(flow[column], errors="coerce").dropna()
        return float(values.iloc[-1]) if not values.empty else 0.0
    return 0.0


def _history_nets(history: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    if history is None or history.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    if {"FII Net Value (₹ Cr)", "DII Net Value (₹ Cr)"}.issubset(history.columns):
        frame = history.copy()
        frame["Date"] = pd.to_datetime(frame.get("Date"), errors="coerce")
        frame = frame.dropna(subset=["Date"]).sort_values("Date")
        return (
            pd.to_numeric(frame["FII Net Value (₹ Cr)"], errors="coerce").dropna(),
            pd.to_numeric(frame["DII Net Value (₹ Cr)"], errors="coerce").dropna(),
        )
    if {"Category", "Net Value (₹ Cr)"}.issubset(history.columns):
        frame = history.copy()
        frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
        frame["Net Value (₹ Cr)"] = pd.to_numeric(frame["Net Value (₹ Cr)"], errors="coerce")
        frame = frame.dropna(subset=["Date", "Net Value (₹ Cr)"])
        pivot = frame.pivot_table(
            index="Date", columns="Category", values="Net Value (₹ Cr)", aggfunc="sum"
        )
        fii = (
            pivot.filter(regex="FII", axis=1).sum(axis=1)
            if not pivot.empty
            else pd.Series(dtype=float)
        )
        dii = (
            pivot.filter(regex="DII", axis=1).sum(axis=1)
            if not pivot.empty
            else pd.Series(dtype=float)
        )
        return fii, dii
    return pd.Series(dtype=float), pd.Series(dtype=float)


def _trend_component(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if len(values) < 4:
        return 0.0
    recent = float(values.iloc[-3:].mean())
    prior = float(values.iloc[-6:-3].mean()) if len(values) >= 6 else float(values.iloc[:-3].mean())
    return _bounded(recent - prior, 2500.0)


def _breadth_component(sector_summary: pd.DataFrame) -> float:
    if sector_summary is None or sector_summary.empty:
        return 0.0
    stocks = pd.to_numeric(sector_summary.get("Stocks"), errors="coerce").fillna(0)
    adv = pd.to_numeric(sector_summary.get("Advancers"), errors="coerce").fillna(0)
    dec = pd.to_numeric(sector_summary.get("Decliners"), errors="coerce").fillna(0)
    total = float(stocks.sum())
    return float((adv.sum() - dec.sum()) / total) if total > 0 else 0.0


def _mean_component(frame: pd.DataFrame, column: str, scale: float) -> float:
    if frame is None or frame.empty or column not in frame.columns:
        return 0.0
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    return _bounded(float(values.mean()), scale) if not values.empty else 0.0


def compute_institutional_momentum(
    flow: pd.DataFrame | None = None,
    history: pd.DataFrame | None = None,
    board: pd.DataFrame | None = None,
    sector_summary: pd.DataFrame | None = None,
) -> dict[str, object]:
    """Return a transparent 0-100 composite from available market inputs."""
    fii = _latest_net(flow, "FII")
    dii = _latest_net(flow, "DII")
    combined = fii + dii
    fii_hist, dii_hist = _history_nets(history)
    flow_trend = (_trend_component(fii_hist) + _trend_component(dii_hist)) / 2
    breadth = _breadth_component(sector_summary)
    sector = _mean_component(sector_summary, "Avg change %", 2.0)
    market = _mean_component(board, "Today change %", 2.0)
    relative = _mean_component(board, "Relative Strength", 2.0)
    components = {
        "Latest institutional flow": round(_bounded(combined, 5000.0), 3),
        "Institutional flow trend": round(flow_trend, 3),
        "Market breadth": round(breadth, 3),
        "Sector momentum": round(sector, 3),
        "Market momentum": round(market, 3),
        "Relative strength": round(relative, 3),
    }
    weights = {
        "Latest institutional flow": 25,
        "Institutional flow trend": 25,
        "Market breadth": 15,
        "Sector momentum": 10,
        "Market momentum": 15,
        "Relative strength": 10,
    }
    weighted = sum(components[key] * weight for key, weight in weights.items()) / 100
    score = max(0.0, min(100.0, 50.0 + 50.0 * weighted))
    if score >= 75:
        label = "STRONG POSITIVE"
    elif score >= 60:
        label = "POSITIVE"
    elif score >= 40:
        label = "NEUTRAL"
    elif score >= 25:
        label = "NEGATIVE"
    else:
        label = "STRONG NEGATIVE"
    explanation = (
        "Components are normalized to -1..+1 and combined with fixed weights: "
        "institutional flow 25%, flow trend 25%, breadth 15%, sector momentum 10%, "
        "market momentum 15%, and relative strength 10%. Missing inputs contribute neutral (0)."
    )
    return {"score": score, "label": label, "components": components, "explanation": explanation}
