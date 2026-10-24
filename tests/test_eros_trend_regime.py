import pandas as pd

from scanner.eros_trend_regime import analyze_eros_trend_regime


def _confidence(consensus: list[str], bands: list[str], scores: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Trend Consensus": consensus,
            "Confidence": bands,
            "Trend Confidence %": scores,
        }
    )


def test_rising_regime_and_breadth():
    result = analyze_eros_trend_regime(
        _confidence(
            ["RISING CONFIRMED", "RISING CONFIRMED", "FALLING CONFIRMED", "MIXED"],
            ["HIGH", "MODERATE", "LOW", "LOW"],
            [90, 70, 40, 20],
        )
    )

    row = result.iloc[0]
    assert row["Regime"] == "RISING DOMINANT"
    assert row["Rising Breadth %"] == 66.67
    assert row["Falling Breadth %"] == 33.33
    assert row["Average Trend Confidence %"] == 55.0


def test_balanced_regime():
    result = analyze_eros_trend_regime(
        _confidence(
            ["RISING CONFIRMED", "FALLING CONFIRMED", "MIXED"],
            ["HIGH", "HIGH", "MODERATE"],
            [80, 80, 60],
        )
    )

    assert result.loc[0, "Regime"] == "BALANCED"
    assert result.loc[0, "Signals"] == 3


def test_insufficient_data_when_no_confirmed_direction():
    result = analyze_eros_trend_regime(
        _confidence(
            ["MIXED", "INSUFFICIENT DATA"],
            ["LOW", "INSUFFICIENT DATA"],
            [20, 0],
        )
    )

    assert result.loc[0, "Regime"] == "INSUFFICIENT DATA"
    assert result.loc[0, "Rising Breadth %"] == 0.0
    assert result.loc[0, "Falling Breadth %"] == 0.0


def test_empty_or_invalid_input_returns_empty():
    assert analyze_eros_trend_regime(None).empty
    assert analyze_eros_trend_regime(pd.DataFrame()).empty
    assert analyze_eros_trend_regime(pd.DataFrame({"Confidence": ["HIGH"]})).empty
