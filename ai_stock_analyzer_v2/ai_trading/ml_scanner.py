"""Multi-stock ML scanner for AI trading intelligence."""

from __future__ import annotations

import pandas as pd

from ai_trading.adaptive_engine import (
    apply_adaptive_confidence,
    build_adaptive_adjustments,
)
from ai_trading.features import build_features
from ai_trading.ml_model import predict_latest, train_model
from ai_trading.outcome_learning import confidence_bucket
from ai_trading.regime_context import build_regime_context
from ai_trading.regime_decision import build_regime_aware_decision
from services.resilient_market_data import download_symbol_frames


def scan_frames(
    frames: dict[str, pd.DataFrame],
    *,
    exchange: str = "NSE",
    horizon: int = 5,
    threshold: float = 0.01,
    adaptive_history: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Train and validate one ML model per symbol and return ranked results."""
    exchange = exchange.upper()
    if exchange not in {"NSE", "BSE"}:
        raise ValueError("exchange must be NSE or BSE")

    adjustments = (
        build_adaptive_adjustments(adaptive_history)
        if adaptive_history is not None
        else pd.DataFrame()
    )
    rows: list[dict[str, object]] = []
    for symbol, frame in frames.items():
        try:
            model, validation = train_model(
                frame,
                horizon=horizon,
                threshold=threshold,
            )
            prediction = predict_latest(model, frame)
            latest_features = build_features(frame).iloc[-1]
            return_score = max(-1.0, min(1.0, float(latest_features["return_5"]) * 4.0))
            ema_score = max(-1.0, min(1.0, float(latest_features["ema_gap"]) * 5.0))
            trend_score = (return_score + ema_score) / 2.0
            regime = build_regime_context(frame)
            decision = build_regime_aware_decision(
                probability_up=float(prediction["probability_up"]),
                accuracy=validation.accuracy,
                roc_auc=validation.roc_auc,
                trend_score=trend_score,
                regime=str(regime["regime"]),
                regime_strength=float(regime["regime_strength_pct"]) / 100.0,
            )
        except (TypeError, ValueError, KeyError):
            continue

        raw_confidence = decision.confidence_pct
        adaptive_confidence = apply_adaptive_confidence(
            raw_confidence,
            signal=decision.signal,
            regime=str(regime["regime"]),
            adjustments=adjustments,
        )
        rows.append(
            {
                "symbol": str(symbol).upper(),
                "exchange": exchange,
                "latest_price": round(float(frame["Close"].dropna().iloc[-1]), 2),
                "probability_up_pct": round(float(prediction["probability_up"]) * 100, 1),
                "signal": decision.signal,
                "confidence_pct": adaptive_confidence,
                "raw_confidence_pct": raw_confidence,
                "adaptive_adjustment_pct": round(adaptive_confidence - raw_confidence, 1),
                "adaptive_samples": _adaptive_samples(
                    adjustments,
                    signal=decision.signal,
                    regime=str(regime["regime"]),
                    confidence_pct=raw_confidence,
                ),
                "model_confidence_pct": decision.model_confidence_pct,
                "validation_pct": decision.validation_pct,
                "trend_pct": decision.trend_pct,
                "regime": regime["regime"],
                "regime_score": regime["regime_score"],
                "regime_strength_pct": regime["regime_strength_pct"],
                "decision_reason": decision.reason,
                "accuracy_pct": round(validation.accuracy * 100, 1),
                "roc_auc": round(validation.roc_auc, 3) if validation.roc_auc is not None else None,
                "train_samples": validation.train_samples,
                "test_samples": validation.test_samples,
            }
        )

    columns = [
        "symbol",
        "exchange",
        "latest_price",
        "probability_up_pct",
        "confidence_pct",
        "raw_confidence_pct",
        "adaptive_adjustment_pct",
        "adaptive_samples",
        "signal",
        "model_confidence_pct",
        "validation_pct",
        "trend_pct",
        "regime",
        "regime_score",
        "regime_strength_pct",
        "decision_reason",
        "accuracy_pct",
        "roc_auc",
        "train_samples",
        "test_samples",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)

    return (
        pd.DataFrame(rows, columns=columns)
        .sort_values(
            ["confidence_pct", "roc_auc", "probability_up_pct"],
            ascending=False,
        )
        .reset_index(drop=True)
    )


def _adaptive_samples(
    adjustments: pd.DataFrame,
    *,
    signal: str,
    regime: str,
    confidence_pct: float,
) -> int:
    """Return the sample count supporting the applied adaptive adjustment."""
    if adjustments.empty:
        return 0
    bucket = confidence_bucket(confidence_pct)
    exact = adjustments[
        (adjustments["signal"] == signal)
        & (adjustments["regime"] == regime)
        & (adjustments["confidence_bucket"] == bucket)
    ]
    fallback = adjustments[
        (adjustments["signal"] == signal)
        & (adjustments["regime"] == "ALL")
        & (adjustments["confidence_bucket"] == bucket)
    ]
    matches = exact if not exact.empty else fallback
    return int(matches.iloc[0]["samples"]) if not matches.empty else 0


def scan_universe(
    symbols: list[str],
    *,
    exchange: str = "NSE",
    period: str = "5y",
    horizon: int = 5,
    threshold: float = 0.01,
    adaptive_history: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Download market history and run the ML model across a stock universe."""
    exchange = exchange.upper()
    if exchange not in {"NSE", "BSE"}:
        raise ValueError("exchange must be NSE or BSE")
    if not symbols:
        return pd.DataFrame()
    suffix = ".NS" if exchange == "NSE" else ".BO"
    tickers = [
        (
            str(symbol).strip().upper()
            if str(symbol).upper().endswith(suffix)
            else f"{str(symbol).strip().upper()}{suffix}"
        )
        for symbol in symbols
    ]
    frames_by_ticker, diagnostics = download_symbol_frames(
        tickers,
        period=period,
        interval="1d",
        auto_adjust=False,
        batch_size=10,
        timeout=15,
    )
    frames: dict[str, pd.DataFrame] = {}
    for symbol, ticker in zip(symbols, tickers, strict=True):
        try:
            frame = frames_by_ticker.get(ticker, pd.DataFrame()).copy()
            frame = frame.dropna(how="all")
            if not frame.empty and "Close" in frame.columns:
                frames[str(symbol).upper().removesuffix(suffix)] = frame
        except (KeyError, TypeError):
            continue

    if not frames:
        empty = pd.DataFrame()
        empty.attrs["scan_diagnostics"] = diagnostics
        return empty

    result = scan_frames(
        frames,
        exchange=exchange,
        horizon=horizon,
        threshold=threshold,
        adaptive_history=adaptive_history,
    )
    result.attrs["scan_diagnostics"] = diagnostics
    return result
