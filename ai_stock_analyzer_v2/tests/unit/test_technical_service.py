import pandas as pd

from services import technical_service


def test_get_price_history_excludes_zero_volume_rows(monkeypatch):
    dates = pd.date_range("2026-10-01", periods=4, freq="D")
    frame = pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0, 103.0],
            "High": [101.0, 102.0, 103.0, 104.0],
            "Low": [99.0, 100.0, 101.0, 102.0],
            "Close": [100.5, 101.5, 102.5, 103.5],
            "Volume": [1000, 0, 1200, 1300],
        },
        index=dates,
    )

    monkeypatch.setattr(
        technical_service,
        "download_symbol_frames",
        lambda *args, **kwargs: ({"RELIANCE.NS": frame}, []),
    )

    result = technical_service.get_price_history("RELIANCE.NS")

    assert result is not None
    assert len(result) == 3
    assert dates[1] not in result.index
    assert (result["Volume"] > 0).all()


def test_get_price_history_returns_none_when_all_rows_have_zero_volume(monkeypatch):
    frame = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [101.0],
            "Low": [99.0],
            "Close": [100.5],
            "Volume": [0],
        },
        index=pd.date_range("2026-10-01", periods=1),
    )

    monkeypatch.setattr(
        technical_service,
        "download_symbol_frames",
        lambda *args, **kwargs: ({"RELIANCE.NS": frame}, []),
    )

    assert technical_service.get_price_history("RELIANCE.NS") is None
