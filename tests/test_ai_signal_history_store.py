from datetime import UTC, datetime

import pytest

from ai_trading.signal_history import attach_outcomes, record_signal
from ai_trading.signal_history_store import load_signal_snapshot, save_signal_snapshot


def _record():
    return record_signal(
        symbol="RELIANCE",
        exchange="NSE",
        signal="LONG",
        probability_up=0.7,
        confidence_pct=65.0,
        validation_pct=72.0,
        trend_pct=60.0,
        entry_price=100.0,
        adjusted_entry_price=99.5,
        horizon_days=5,
        timestamp=datetime(2026, 10, 1, tzinfo=UTC),
    )


def test_signal_snapshot_survives_a_new_store_connection(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SIGNAL_HISTORY_DATABASE_PATH", str(tmp_path / "signals.sqlite3"))
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    record = _record()
    assert save_signal_snapshot([record]) == 1

    loaded_records, loaded_history = load_signal_snapshot()

    assert len(loaded_records) == 1
    assert loaded_records[0] == record
    assert loaded_history.loc[0, "symbol"] == "RELIANCE"
    assert bool(loaded_history.loc[0, "completed"]) is False


def test_signal_snapshot_upsert_persists_outcome_without_duplicate_rows(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("AI_SIGNAL_HISTORY_DATABASE_PATH", str(tmp_path / "signals.sqlite3"))
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    record = _record()
    history = attach_outcomes([record], {"RELIANCE": 110.0})

    assert save_signal_snapshot([record], history) == 1
    assert save_signal_snapshot([record], history) == 1

    loaded_records, loaded_history = load_signal_snapshot()

    assert len(loaded_records) == 1
    assert len(loaded_history) == 1
    assert bool(loaded_history.loc[0, "completed"]) is True
    assert loaded_history.loc[0, "return_pct"] == pytest.approx(
        (110.0 / 99.5 - 1.0) * 100.0
    )
