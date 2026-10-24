import numpy as np
import pandas as pd

from algorithmic_trading.trading_journal import (
    ReconciliationStatus,
    TradeExecution,
    TradeOrder,
    add_journal_entry,
    add_journal_streaks,
    bulls_eye,
    consecutive_losses,
    drawdown_stats,
    journal_ai_prompts,
    journal_score,
    mae,
    merge_journal_sessions,
    reconcile_orders,
    reconciliation_summary,
)


def test_reconcile_matched_missed_and_override() -> None:
    orders = [
        TradeOrder("O1", "RELIANCE", 100),
        TradeOrder("O2", "TCS", -50),
    ]
    executions = [
        TradeExecution("E1", "RELIANCE", 100, 1_000),
        TradeExecution("E2", "INFY", 25, 1_500),
    ]

    records = reconcile_orders(orders, executions)
    summary = reconciliation_summary(records)

    assert summary == {"matched": 1, "missed": 1, "override": 1}
    assert records[0].status == ReconciliationStatus.MATCHED
    assert records[1].status == ReconciliationStatus.MISSED
    assert records[2].status == ReconciliationStatus.OVERRIDE


def test_add_journal_entry() -> None:
    entries = []
    entry = add_journal_entry(entries, "2026-09-28", "evening", "Followed the plan.")

    assert entries == [entry]
    assert entry.phase == "evening"


def test_blank_journal_entry_is_rejected() -> None:
    entries = []

    try:
        add_journal_entry(entries, "", "morning", "note")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_bulls_eye_directional_accuracy() -> None:
    assert bulls_eye(2.0, 1.0) == 1
    assert bulls_eye(-2.0, 1.0) == -1
    assert bulls_eye(0.0, 1.0) == 0
    assert bulls_eye(None, 1.0) is None


def test_journal_score_reaches_120_for_complete_entry() -> None:
    row = {
        "checklist_done": 1,
        "mindset_pre": 3,
        "confidence_pre": 4,
        "perf_forecast": 1.0,
        "bc_1": "market trend",
        "bc_2": "risk controlled",
        "mindset_post": 3,
        "confidence_post": 4,
        "perf_actual": 1.5,
        "what_went_well_1": "followed plan",
        "what_went_well_2": "managed risk",
        "what_went_well_3": "journaled",
        "tomorrows_kaizen": "improve entry timing",
        "notes": "clean execution",
        "gratitude_1": "health",
        "gratitude_2": "family",
        "gratitude_3": "learning",
    }
    assert journal_score(row) == 120


def test_journal_streak_forgives_one_missed_weekday() -> None:
    journal = pd.DataFrame({"date": ["2026-09-21", "2026-09-22", "2026-09-24", "2026-09-25"]})
    result = add_journal_streaks(journal)
    assert result["streak"].tolist() == [1, 2, 3, 4]
    assert result["multiplier"].tolist() == [1.05, 1.10, 1.15, 1.20]


def test_merge_journal_sessions_computes_metrics() -> None:
    pre = pd.DataFrame([{"_id": "p1", "date": "2026-09-28", "perf_forecast": 2.0}])
    post = pd.DataFrame([{"_id": "p2", "date": "2026-09-28", "perf_actual": -1.0}])
    result = merge_journal_sessions(pre, post)
    assert result.loc[0, "bulls_eye"] == -1
    assert result.loc[0, "final_score"] >= 0


def test_mae_handles_short_and_long_trades() -> None:
    prices = pd.Series(
        [100.0, 110.0, 90.0],
        index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
    )
    trades = pd.DataFrame(
        [
            {
                "entry_date": pd.Timestamp("2026-01-01"),
                "exit_date": pd.Timestamp("2026-01-03"),
                "price_exec": 100.0,
                "quantity_exec": -10,
            },
            {
                "entry_date": pd.Timestamp("2026-01-01"),
                "exit_date": pd.Timestamp("2026-01-03"),
                "price_exec": 100.0,
                "quantity_exec": 10,
            },
        ]
    )
    result = mae(trades, prices)
    assert np.allclose(result.to_numpy(), [10.0, 10.0])


def test_drawdown_stats_and_consecutive_losses() -> None:
    drawdown = drawdown_stats([10, -5, -10, 20])
    assert drawdown["count"] == 1
    assert drawdown["max_dur"] == 2
    losses = consecutive_losses(["win", "loss", "loss", "breakeven", "loss"])
    assert losses == {"max_run": 2, "avg_run": 1.5}


def test_journal_ai_prompts_cover_review_workflows() -> None:
    prompts = journal_ai_prompts()
    assert {"weekly", "kaizen", "strengths", "monthly", "streak_recovery"} <= prompts.keys()
