import pandas as pd
import pytest

from ai_trading.self_improving import evaluate_retraining_need


def _history() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "completed": [True] * 30,
            "return_pct": [1.0] * 20 + [-1.0] * 10,
            "confidence_pct": [70.0] * 30,
        }
    )


def test_retraining_is_due_when_recent_results_degrade() -> None:
    decision = evaluate_retraining_need(
        _history(),
        min_samples=20,
        lookback=30,
        min_win_rate_pct=70.0,
    )
    assert decision.should_retrain is True
    assert decision.reason == "RETRAIN DUE"
    assert decision.recent_win_rate_pct == pytest.approx(66.67, abs=0.01)


def test_stable_history_does_not_trigger_retraining() -> None:
    history = _history()
    history["return_pct"] = 1.0
    decision = evaluate_retraining_need(history, min_samples=20)
    assert decision.should_retrain is False
    assert decision.reason == "MODEL STABLE"


def test_insufficient_history() -> None:
    decision = evaluate_retraining_need(_history().head(5), min_samples=10)
    assert decision.reason == "INSUFFICIENT SAMPLES"


def test_invalid_parameters() -> None:
    with pytest.raises(ValueError):
        evaluate_retraining_need(_history(), min_samples=0)
