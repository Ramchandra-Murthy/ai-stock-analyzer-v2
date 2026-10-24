"""FastAPI backend for EROS intraday market scanning.

This API is introduced alongside the existing Streamlit UI. The Streamlit
application remains the presentation layer until the new frontend is ready.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from api.scan_history import recent_scans
from api.scan_manager import ErosScanManager
from config.env import load_environment
from scanner.market_scanner import market_scan
from scanner.price_jump import scan_price_jumps
from scanner.unusual_activity import scan_unusual_activity
from services.analyzer import analyze_stock
from services.intraday_exchange_summary import exchange_summary
from services.intraday_health import assess_scan_health
from services.options_analytics import fetch_option_chain, summarize_option_chain

load_environment()

app = FastAPI(
    title="EROS Market API",
    version="1.0.0",
    description="Backend API for the EROS intraday NSE/BSE scanner.",
)

_SCAN_MANAGER = ErosScanManager(max_workers=1)


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame to JSON-safe records."""
    if frame is None or frame.empty:
        return []
    clean = frame.copy()
    clean = clean.astype(object).where(pd.notna(clean), None)
    return clean.to_dict(orient="records")


def _stats(frame: pd.DataFrame) -> dict[str, Any]:
    """Return scanner diagnostics attached to a DataFrame."""
    return dict(getattr(frame, "attrs", {}).get("scan_stats", {}))


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """Serve the EROS browser dashboard."""
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    """Lightweight health check that never runs a market scan."""
    return {"status": "ok", "service": "eros-api"}


@app.get("/api/v1/intraday/price-jumps")
def price_jumps(
    limit: int = Query(20, ge=1, le=100),
    cap_category: str = Query("All caps"),
    exchange_category: str = Query("Both"),
    lookback_minutes: int = Query(5, ge=1, le=60),
    jump_percent: float = Query(1.0, ge=0.0, le=100.0),
) -> dict[str, Any]:
    """Return current EROS price-pulse candidates and scan diagnostics."""
    try:
        frame = scan_price_jumps(
            limit=limit,
            cap_category=cap_category,
            exchange_category=exchange_category,
            lookback_minutes=lookback_minutes,
            jump_percent=jump_percent,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Price-pulse scan failed: {exc}") from exc

    return {
        "count": len(frame),
        "results": _records(frame),
        "scan_stats": _stats(frame),
    }


@app.post("/api/v1/intraday/price-jumps/start")
def start_price_jumps(
    limit: int = Query(20, ge=1, le=100),
    cap_category: str = Query("All caps"),
    exchange_category: str = Query("Both"),
    lookback_minutes: int = Query(5, ge=1, le=60),
    jump_percent: float = Query(1.0, ge=0.0, le=100.0),
) -> dict[str, str]:
    """Start a non-blocking EROS price-jump scan."""
    job_id = _SCAN_MANAGER.start_price_jump_scan(
        limit=limit,
        cap_category=cap_category,
        exchange_category=exchange_category,
        lookback_minutes=lookback_minutes,
        jump_percent=jump_percent,
    )
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/v1/intraday/price-jumps/jobs/{job_id}")
def price_jump_job(job_id: str) -> dict[str, Any]:
    """Return the state or completed result of a background scan."""
    job = _SCAN_MANAGER.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Scan job not found.")
    return job


@app.get("/api/v1/intraday/health")
def intraday_health() -> dict[str, Any]:
    """Return lightweight health and exchange metrics from the latest saved scan."""
    scans = recent_scans(1)
    if not scans:
        return {
            "status": "NO_SCAN",
            "message": "No completed intraday scan is available.",
            "candidates": 0,
            "exchanges": [],
        }

    latest = scans[0]
    observed_at = pd.to_datetime(latest["completed_at"], utc=True).to_pydatetime()
    frame = pd.DataFrame(latest.get("results", []))
    health_result = assess_scan_health(frame, observed_at)
    summary = exchange_summary(frame)

    return {
        **health_result,
        "completed_at": latest["completed_at"],
        "job_id": latest["job_id"],
        "exchanges": _records(summary),
    }


@app.get("/api/v1/intraday/history")
def scan_history(
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Return recent persisted EROS price-pulse scans."""
    return {"count": limit, "scans": recent_scans(limit)}


@app.get("/api/v1/intraday/unusual-activity")
def unusual_activity(
    limit: int = Query(20, ge=1, le=100),
    cap_category: str = Query("All caps"),
    exchange_category: str = Query("Both"),
) -> dict[str, Any]:
    """Return current unusual price/volume activity."""
    try:
        frame = scan_unusual_activity(
            limit=limit,
            cap_category=cap_category,
            exchange_category=exchange_category,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Unusual-activity scan failed: {exc}") from exc

    return {
        "count": len(frame),
        "results": _records(frame),
        "scan_stats": _stats(frame),
    }


@app.get("/api/v1/options/chain")
def options_chain(
    underlying: str = Query("NIFTY", pattern="^(NIFTY|BANKNIFTY|FINNIFTY)$"),
    expiry: str | None = Query(None, min_length=1, max_length=40),
) -> dict[str, Any]:
    """Return normalized index options analytics for the React dashboard."""
    normalized = underlying.strip().upper()
    if expiry is not None and not re.fullmatch(r"[A-Za-z0-9-]{1,40}", expiry):
        raise HTTPException(status_code=400, detail="Invalid option expiry.")

    try:
        result = fetch_option_chain(normalized, expiry)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Options analytics failed: {exc}") from exc

    if expiry is not None and result.expiries and expiry not in result.expiries:
        raise HTTPException(status_code=400, detail="Requested expiry is not available.")

    return {
        "underlying": result.underlying,
        "provider": result.provider_symbol,
        "expiry": result.expiry,
        "spot": result.spot,
        "expiries": list(result.expiries),
        "status": result.status,
        "message": result.message,
        "count": len(result.chain),
        "summary": _records(summarize_option_chain(result.chain)),
        "chain": _records(result.chain),
    }


@app.get("/api/v1/scanner/stock")
def stock_detail(
    symbol: str = Query(..., min_length=1, max_length=30),
    exchange: str = Query("NSE", pattern="^(NSE|BSE)$"),
) -> dict[str, Any]:
    """Return existing analyzer details for one validated stock symbol."""
    normalized = symbol.strip().upper()
    if not re.fullmatch(r"[A-Z0-9&-]{1,20}", normalized):
        raise HTTPException(status_code=400, detail="Invalid stock symbol.")
    ticker = f"{normalized}.{'NS' if exchange == 'NSE' else 'BO'}"
    try:
        result = analyze_stock(ticker)
        last = result["last"]
        signal = result["signal"]
        breakout = result["breakout"]
        observation = signal.get("MarketObservation", {})
        metrics = {}
        for key in (
            "Close",
            "SMA_20",
            "SMA_50",
            "EMA_20",
            "RSI_14",
            "MACD",
            "MACD_Histogram",
            "Upper_Band",
            "Lower_Band",
            "ATR",
        ):
            if key in last and pd.notna(last[key]):
                metrics[key] = float(last[key])

        chart = []
        for index, row in result["df"].tail(60).iterrows():
            point = {"index": int(index)}
            for key in ("Close", "SMA_20", "SMA_50"):
                if key in row and pd.notna(row[key]):
                    point[key] = float(row[key])
            if "Close" in point:
                chart.append(point)

        return {
            "symbol": normalized,
            "exchange": exchange,
            "ticker": ticker,
            "price": metrics.get("Close"),
            "metrics": metrics,
            "trend": result["trend"],
            "signal": signal,
            "breakout": breakout,
            "market_observation": observation,
            "chart": chart,
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Stock analysis failed: {exc}") from exc


@app.get("/api/v1/scanner/market")
def market(
    limit: int = Query(10, ge=1, le=30),
) -> dict[str, Any]:
    """Return the existing broad-market scanner output."""
    try:
        frame = market_scan()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Market scan failed: {exc}") from exc

    return {
        "count": min(len(frame), limit),
        "results": _records(frame.head(limit)),
    }
