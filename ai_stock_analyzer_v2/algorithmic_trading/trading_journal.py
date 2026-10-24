"""Trading journal and order-reconciliation tools for research.

The design follows Chapter 10 of Laurent Bernut's *Algorithmic Short Selling
with Python, Second Edition*: record trades and thoughts, reconcile intended
orders against executions, and preserve an audit trail for later analysis.
This implementation is broker-neutral and stores records in memory so the
existing application remains dependency-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # annotation-only; pandas is imported lazily inside the functions that use it
    import pandas as pd


class ReconciliationStatus(StrEnum):
    """Outcome of comparing an intended order with an execution."""

    MATCHED = "matched"
    MISSED = "missed"
    OVERRIDE = "override"


@dataclass(frozen=True)
class TradeOrder:
    """An intended order."""

    order_id: str
    symbol: str
    quantity: int
    price: float | None = None


@dataclass(frozen=True)
class TradeExecution:
    """An execution reported by a venue or broker."""

    execution_id: str
    symbol: str
    quantity: int
    price: float


@dataclass(frozen=True)
class ReconciliationRecord:
    """Auditable classification of an order/execution pair."""

    status: ReconciliationStatus
    symbol: str
    ordered_quantity: int
    executed_quantity: int
    order_id: str | None
    execution_id: str | None


@dataclass(frozen=True)
class JournalEntry:
    """A dated trading thought or review note."""

    date: str
    phase: str
    text: str


def reconcile_orders(
    orders: list[TradeOrder],
    executions: list[TradeExecution],
) -> list[ReconciliationRecord]:
    """Classify orders and executions as matched, missed or override.

    Matching is by symbol and signed quantity. An execution with no
    corresponding order is an override; an order with no execution is missed.
    """
    execution_by_key = {(item.symbol, item.quantity): item for item in executions}
    matched_execution_ids: set[str] = set()
    records: list[ReconciliationRecord] = []

    for order in orders:
        execution = execution_by_key.get((order.symbol, order.quantity))
        if execution is None:
            records.append(
                ReconciliationRecord(
                    ReconciliationStatus.MISSED,
                    order.symbol,
                    order.quantity,
                    0,
                    order.order_id,
                    None,
                )
            )
            continue

        matched_execution_ids.add(execution.execution_id)
        records.append(
            ReconciliationRecord(
                ReconciliationStatus.MATCHED,
                order.symbol,
                order.quantity,
                execution.quantity,
                order.order_id,
                execution.execution_id,
            )
        )

    for execution in executions:
        if execution.execution_id in matched_execution_ids:
            continue
        records.append(
            ReconciliationRecord(
                ReconciliationStatus.OVERRIDE,
                execution.symbol,
                0,
                execution.quantity,
                None,
                execution.execution_id,
            )
        )

    return records


def reconciliation_summary(
    records: list[ReconciliationRecord],
) -> dict[str, int]:
    """Count each reconciliation outcome."""
    summary = {status.value: 0 for status in ReconciliationStatus}
    for record in records:
        summary[record.status.value] += 1
    return summary


def add_journal_entry(
    entries: list[JournalEntry],
    date: str,
    phase: str,
    text: str,
) -> JournalEntry:
    """Append a validated morning/evening or review entry."""
    if not date.strip():
        raise ValueError("date must not be empty")
    if not phase.strip():
        raise ValueError("phase must not be empty")
    if not text.strip():
        raise ValueError("text must not be empty")

    entry = JournalEntry(date=date, phase=phase, text=text)
    entries.append(entry)
    return entry


def bulls_eye(perf_forecast: float | None, perf_actual: float | None) -> int | None:
    """Compare forecast and actual performance direction."""
    if perf_forecast is None or perf_actual is None:
        return None
    try:
        forecast = float(perf_forecast)
        actual = float(perf_actual)
    except (TypeError, ValueError):
        return None
    product = forecast * actual
    if product > 0:
        return 1
    if product < 0:
        return -1
    return 0


def journal_score(row: dict) -> int:
    """Score journal completeness using the Chapter 10 120-point rubric."""
    score = 20 if row.get("checklist_done") == 1 else 0
    score += 5 if row.get("mindset_pre") is not None else 0
    score += 5 if row.get("confidence_pre") is not None else 0
    score += 5 if row.get("perf_forecast") is not None else 0
    score += 3 if str(row.get("bc_1") or "").strip() else 0
    score += 2 if str(row.get("bc_2") or "").strip() else 0
    score += 5 if row.get("mindset_post") is not None else 0
    score += 5 if row.get("confidence_post") is not None else 0
    score += 5 if row.get("perf_actual") is not None else 0
    score += 5 if str(row.get("what_went_well_1") or "").strip() else 0
    score += 5 if str(row.get("what_went_well_2") or "").strip() else 0
    score += 5 if str(row.get("what_went_well_3") or "").strip() else 0
    score += 20 if str(row.get("tomorrows_kaizen") or "").strip() else 0
    score += 10 if str(row.get("notes") or "").strip() else 0
    gratitude = sum(
        bool(str(row.get(key) or "").strip())
        for key in ("gratitude_1", "gratitude_2", "gratitude_3")
    )
    return score + {0: 0, 1: 6, 2: 12, 3: 20}[gratitude]


def add_journal_streaks(journal: pd.DataFrame) -> pd.DataFrame:
    """Add completion streak and multiplier, forgiving one missed weekday."""
    import pandas as pd

    if journal.empty:
        result = journal.copy()
        result["streak"] = pd.Series(dtype=int)
        result["multiplier"] = pd.Series(dtype=float)
        return result

    result = journal.sort_values("date").copy()
    dates = pd.to_datetime(result["date"])
    streaks: list[int] = []
    streak = 0
    previous = None
    for current in dates:
        if previous is None:
            streak = 1
        else:
            gap = len(pd.bdate_range(previous + pd.Timedelta(days=1), current))
            streak = streak + 1 if gap <= 2 else 1
        streaks.append(streak)
        previous = current

    result["streak"] = streaks
    result["multiplier"] = (1 + result["streak"] / 20).round(2)
    return result


def merge_journal_sessions(
    pre: pd.DataFrame,
    post: pd.DataFrame,
) -> pd.DataFrame:
    """Outer-merge morning and evening journal rows and compute metrics."""
    import pandas as pd

    if pre.empty and post.empty:
        return pd.DataFrame()

    left = pre.rename(columns={"_id": "_pre_id"})
    right = post.rename(columns={"_id": "_post_id"})
    merged = pd.merge(
        left,
        right,
        on="date",
        how="outer",
        suffixes=("_pre", "_post"),
    )
    merged["bulls_eye"] = merged.apply(
        lambda row: bulls_eye(row.get("perf_forecast"), row.get("perf_actual")),
        axis=1,
    )
    merged["score"] = merged.apply(journal_score, axis=1)
    merged = add_journal_streaks(merged)
    merged["final_score"] = (merged["score"] * merged["multiplier"]).round(1)
    return merged


def mae(trades: pd.DataFrame, prices: pd.Series) -> pd.Series:
    """Calculate maximum adverse excursion in percentage points."""
    import pandas as pd

    values: list[float] = []
    for _, trade in trades.iterrows():
        window = prices.loc[trade["entry_date"] : trade["exit_date"]]
        entry = float(trade["price_exec"])
        if window.empty or entry == 0:
            values.append(0.0)
            continue
        if float(trade["quantity_exec"]) < 0:
            adverse = (float(window.max()) - entry) / entry * 100
        else:
            adverse = (entry - float(window.min())) / entry * 100
        values.append(max(0.0, adverse))
    return pd.Series(values, index=trades.index, dtype=float)


def drawdown_stats(pnl) -> dict[str, float | int]:
    """Calculate depth, duration and frequency of trade-level drawdowns."""
    import pandas as pd

    cumulative = pd.Series(pnl, dtype=float).cumsum()
    if cumulative.empty:
        return {
            "max_dd": 0,
            "avg_dd": 0,
            "max_dur": 0,
            "avg_dur": 0,
            "count": 0,
            "freq": 0,
        }

    denominator = cumulative.cummax().clip(lower=1e-9)
    drawdown = (cumulative - cumulative.cummax()) / denominator
    periods: list[tuple[int, int]] = []
    start = None
    for index, in_drawdown in enumerate(drawdown < 0):
        if in_drawdown and start is None:
            start = index
        elif not in_drawdown and start is not None:
            periods.append((start, index - 1))
            start = None
    if start is not None:
        periods.append((start, len(drawdown) - 1))

    if not periods:
        return {
            "max_dd": 0,
            "avg_dd": 0,
            "max_dur": 0,
            "avg_dur": 0,
            "count": 0,
            "freq": 0,
        }

    depths = [float(drawdown.iloc[start : end + 1].min()) for start, end in periods]
    durations = [end - start + 1 for start, end in periods]
    return {
        "max_dd": round(min(depths), 4),
        "avg_dd": round(sum(depths) / len(depths), 4),
        "max_dur": max(durations),
        "avg_dur": round(sum(durations) / len(durations), 1),
        "count": len(periods),
        "freq": round(len(periods) / len(cumulative), 4),
    }


def consecutive_losses(results) -> dict[str, float | int]:
    """Calculate maximum and average consecutive losing runs."""
    runs: list[int] = []
    current = 0
    for result in results:
        if result == "loss":
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return {
        "max_run": max(runs, default=0),
        "avg_run": round(sum(runs) / len(runs), 1) if runs else 0.0,
    }


def journal_ai_prompts() -> dict[str, str]:
    """Return Chapter 10 prompts for external AI psychology review."""
    return {
        "weekly": (
            "Review the last five journal days. Identify recurring mindset, "
            "confidence, checklist and bulls_eye patterns. Compare reasoning "
            "quality with directional accuracy. Focus on execution psychology."
        ),
        "kaizen": (
            "Review 30 days of tomorrows_kaizen entries. Identify recurring "
            "themes, distinguish repeated intentions from evolving behavior, "
            "and suggest one structural friction-reduction change."
        ),
        "strengths": (
            "Review 30 days of what_went_well entries. Identify recurring "
            "strengths and suggest one protocol or habit that reinforces each."
        ),
        "monthly": (
            "Review one month of journal data. Describe dominant emotional "
            "patterns and recurring themes, then identify the single most "
            "important execution-psychology pattern to address next month."
        ),
        "streak_recovery": (
            "Review the seven days surrounding a broken journal streak. "
            "Identify what changed before the gap and suggest one concrete "
            "friction-reduction change."
        ),
    }
