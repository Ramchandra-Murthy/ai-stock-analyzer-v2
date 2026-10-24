import pandas as pd
import pytest

from algorithmic_trading.entry_rule_research import compare_entry_rules


def test_compare_entry_rules_uses_shared_assumptions_and_metrics() -> None:
    index = pd.date_range("2026-01-01", periods=5, freq="D")
    prices = pd.Series([100.0, 102.0, 101.0, 104.0, 103.0], index=index)
    momentum = pd.Series([1.0, 1.0, 1.0, 0.0, 0.0], index=index)
    mean_reversion = pd.Series([0.0, -1.0, -1.0, 0.0, 0.0], index=index)

    comparison = compare_entry_rules(
        {"momentum": (prices, momentum), "mean_reversion": (prices, mean_reversion)},
        cost_bps=0,
    )

    assert comparison.index.name == "entry_rule"
    assert comparison.index.tolist() == ["momentum", "mean_reversion"]
    assert {"total_return", "max_drawdown", "trade_count", "sharpe_ratio"} <= set(
        comparison.columns
    )


def test_compare_entry_rules_same_rule_produces_same_metrics() -> None:
    index = pd.date_range("2026-01-01", periods=4, freq="D")
    prices = pd.Series([100.0, 101.0, 99.0, 102.0], index=index)
    signals = pd.Series([1.0, 1.0, 0.0, 0.0], index=index)

    comparison = compare_entry_rules(
        {"rule_a": (prices, signals), "rule_b": (prices, signals)},
        cost_bps=0,
    )

    assert comparison.loc["rule_a"].to_dict() == comparison.loc["rule_b"].to_dict()


def test_compare_entry_rules_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="at least one entry rule"):
        compare_entry_rules({})


@pytest.mark.parametrize("name", ["", "   "])
def test_compare_entry_rules_rejects_blank_names(name: str) -> None:
    index = pd.date_range("2026-01-01", periods=2, freq="D")
    prices = pd.Series([100.0, 101.0], index=index)
    signals = pd.Series([0.0, 1.0], index=index)

    with pytest.raises(ValueError, match="non-empty strings"):
        compare_entry_rules({name: (prices, signals)})
