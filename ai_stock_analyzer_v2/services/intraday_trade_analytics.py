"""Descriptive trade-journal performance analytics."""

from __future__ import annotations

import pandas as pd

# fmt: off


def trade_performance_frame(history: list[dict] | None) -> pd.DataFrame:
    """Return journal rows with realized R multiple where available."""
    frame = pd.DataFrame(history or [])
    if frame.empty:
        return frame
    result = frame.copy()
    risk = pd.to_numeric(result.get("Risk"), errors="coerce")
    pnl = pd.to_numeric(result.get("PnL"), errors="coerce")
    result["R Multiple"] = (pnl / risk).where(risk > 0)
    return result


def performance_summary(history: list[dict] | None) -> pd.DataFrame:
    """Return descriptive closed-trade statistics."""
    frame = trade_performance_frame(history)
    if frame.empty:
        return pd.DataFrame([_summary_row(0, 0, 0, 0, 0.0, 0.0)])
    pnl = pd.to_numeric(frame["PnL"], errors="coerce")
    closed = frame[pnl.notna()].copy()
    if closed.empty:
        return pd.DataFrame([_summary_row(len(frame), 0, 0, 0, 0.0, 0.0)])
    wins = int((closed["PnL"] > 0).sum())
    losses = int((closed["PnL"] < 0).sum())
    return pd.DataFrame(
        [
            {
                "Trades": len(frame),
                "Closed": len(closed),
                "Wins": wins,
                "Losses": losses,
                "Win rate %": round(wins / len(closed) * 100, 2),
                "Net PnL": round(float(closed["PnL"].sum()), 2),
                "Average R": round(float(closed["R Multiple"].mean()), 2),
            }
        ]
    )


def _summary_row(
    trades: int,
    closed: int,
    wins: int,
    losses: int,
    win_rate: float,
    net_pnl: float,
) -> dict:
    """Build the empty-performance summary row."""
    return {
        "Trades": trades,
        "Closed": closed,
        "Wins": wins,
        "Losses": losses,
        "Win rate %": win_rate,
        "Net PnL": net_pnl,
    }


def _group_performance(history: list[dict] | None, group_column: str) -> pd.DataFrame:
    """Group realized journal results by a requested journal column."""
    frame = trade_performance_frame(history)
    columns = [group_column, "Trades", "Closed", "Win rate %", "Net PnL", "Average R"]
    if frame.empty or group_column not in frame.columns:
        return pd.DataFrame(columns=columns)
    frame["PnL"] = pd.to_numeric(frame["PnL"], errors="coerce")
    rows = []
    for group_name, group in frame.groupby(group_column, dropna=False):
        closed = group[group["PnL"].notna()]
        wins = int((closed["PnL"] > 0).sum())
        rows.append(
            {
                group_column: str(group_name),
                "Trades": len(group),
                "Closed": len(closed),
                "Win rate %": round(wins / len(closed) * 100, 2) if len(closed) else 0.0,
                "Net PnL": round(float(closed["PnL"].sum()), 2) if len(closed) else 0.0,
                "Average R": (
                    round(float(closed["R Multiple"].mean()), 2) if len(closed) else 0.0
                ),
            }
        )
    return pd.DataFrame(rows)


def setup_performance(history: list[dict] | None) -> pd.DataFrame:
    """Group realized journal results by setup."""
    return _group_performance(history, "Setup")


def side_performance(history: list[dict] | None) -> pd.DataFrame:
    """Group realized journal results by LONG/SHORT side."""
    return _group_performance(history, "Side")
