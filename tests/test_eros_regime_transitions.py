import pandas as pd

from scanner.eros_regime_transitions import analyze_eros_regime_transitions


def _history(regimes):
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-20 09:15", periods=len(regimes), freq="5min"),
            "Regime": regimes,
        }
    )


def test_detects_neutral_and_directional_transitions():
    result = analyze_eros_regime_transitions(
        _history(
            [
                "BALANCED",
                "RISING DOMINANT",
                "RISING DOMINANT",
                "FALLING DOMINANT",
                "BALANCED",
                "FALLING DOMINANT",
            ]
        )
    )

    assert result["Transition"].tolist() == [
        "BALANCED → RISING DOMINANT",
        "RISING DOMINANT → FALLING DOMINANT",
        "FALLING DOMINANT → BALANCED",
        "BALANCED → FALLING DOMINANT",
    ]
    assert result["Direction Transition"].tolist() == [
        "NEUTRAL → RISING",
        "RISING → FALLING",
        "FALLING → NEUTRAL",
        "NEUTRAL → FALLING",
    ]
    assert result["Transition Type"].tolist() == [
        "FROM NEUTRAL",
        "DIRECTION REVERSAL",
        "TO NEUTRAL",
        "FROM NEUTRAL",
    ]
    assert result["Transition Count"].tolist() == [1, 2, 3, 4]


def test_transition_timestamps_are_preserved():
    result = analyze_eros_regime_transitions(
        _history(["BALANCED", "RISING DOMINANT", "FALLING DOMINANT"])
    )

    assert result["Timestamp"].tolist() == [
        pd.Timestamp("2026-09-20 09:20"),
        pd.Timestamp("2026-09-20 09:25"),
    ]


def test_single_snapshot_has_no_transition():
    result = analyze_eros_regime_transitions(_history(["BALANCED"]))
    assert result.empty


def test_invalid_input_returns_empty():
    assert analyze_eros_regime_transitions(None).empty
    assert analyze_eros_regime_transitions(pd.DataFrame()).empty
    assert analyze_eros_regime_transitions(pd.DataFrame({"Regime": ["BALANCED"]})).empty
