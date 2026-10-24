import pandas as pd

from scanner.eros_fusion import compute_eros_fusion


def test_fusion_combines_available_components():
    confluence = pd.DataFrame(
        {
            "Symbol": ["AAA", "BBB"],
            "Exchange": ["NSE", "NSE"],
            "Confluence Score": [90.0, 60.0],
        }
    )
    history = pd.DataFrame(
        {
            "Timestamp": pd.to_datetime(["2026-09-18 10:00", "2026-09-18 10:02"]),
            "Symbol": ["AAA", "AAA"],
            "Exchange": ["NSE", "NSE"],
        }
    )
    jumps = pd.DataFrame({"Symbol": ["AAA"], "Exchange": ["NSE"]})
    result = compute_eros_fusion(
        confluence,
        history,
        jumps,
        {"score": 80.0},
    )
    assert result.iloc[0]["Symbol"] == "AAA"
    assert result.iloc[0]["Fusion Score"] > result.iloc[1]["Fusion Score"]
    assert result.iloc[0]["Fusion Coverage"] == 4


def test_empty_confluence_returns_empty():
    assert compute_eros_fusion(pd.DataFrame()).empty


def test_price_jump_persistence_replaces_binary_presence_component():
    confluence = pd.DataFrame(
        {
            "Symbol": ["AAA", "BBB"],
            "Exchange": ["NSE", "NSE"],
            "Confluence Score": [80.0, 80.0],
        }
    )
    jumps = pd.DataFrame({"Symbol": ["AAA", "BBB"], "Exchange": ["NSE", "NSE"]})
    jump_history = pd.DataFrame(
        {
            "Timestamp": pd.to_datetime(
                ["2026-09-18 10:00", "2026-09-18 10:05", "2026-09-18 10:10"]
            ),
            "Symbol": ["AAA", "AAA", "AAA"],
            "Exchange": ["NSE", "NSE", "NSE"],
        }
    )

    result = compute_eros_fusion(
        confluence,
        None,
        jumps,
        {"score": 50.0},
        jump_history,
    )

    aaa = result.loc[result["Symbol"] == "AAA"].iloc[0]
    bbb = result.loc[result["Symbol"] == "BBB"].iloc[0]
    assert aaa["Price Jump Component"] == 60.0
    assert bbb["Price Jump Component"] == 0.0
