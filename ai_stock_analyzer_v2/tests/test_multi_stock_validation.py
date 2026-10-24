import pandas as pd

from algorithmic_trading.multi_stock_validation import evaluate_symbol_universe


def _frame(length: int = 80) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=length, freq="B")
    close = pd.Series([100.0 + i * 0.2 for i in range(length)], index=index)
    return pd.DataFrame(
        {"High": close + 1.0, "Low": close - 1.0, "Close": close},
        index=index,
    )


def test_universe_validation_returns_fold_rows_and_skips_short_history() -> None:
    frame = _frame()
    benchmark = frame["Close"]
    result = evaluate_symbol_universe(
        {"AAA": frame, "SHORT": _frame(20)},
        benchmark,
        min_train_size=10,
        n_splits=2,
        minimum_observations=30,
        cost_bps=0.0,
    )

    valid = result[result["symbol"] == "AAA"]
    skipped = result[result["symbol"] == "SHORT"]

    assert valid["status"].eq("ok").all()
    assert valid["fold"].tolist() == [1, 2]
    assert skipped["status"].tolist() == ["skipped"]
    assert "insufficient observations" in skipped.iloc[0]["reason"]
    assert skipped.iloc[0]["skip_category"] == "insufficient_history"


def test_universe_validation_reports_missing_columns_without_aborting() -> None:
    result = evaluate_symbol_universe(
        {"BAD": pd.DataFrame({"Close": [100.0, 101.0]})},
        pd.Series([100.0, 101.0]),
        min_train_size=2,
        n_splits=1,
        minimum_observations=2,
    )

    assert result.iloc[0]["symbol"] == "BAD"
    assert result.iloc[0]["status"] == "skipped"
    assert "missing required columns" in result.iloc[0]["reason"]
    assert result.iloc[0]["skip_category"] == "missing_market_data"


def test_universe_validation_excludes_nonpositive_and_infinite_prices() -> None:
    frame = _frame(80)
    frame.loc[frame.index[5], "Close"] = 0.0
    frame.loc[frame.index[6], "Close"] = float("inf")
    result = evaluate_symbol_universe(
        {"AAA": frame},
        _frame(80)["Close"],
        min_train_size=10,
        n_splits=2,
        minimum_observations=30,
        cost_bps=0.0,
    )

    assert result["status"].eq("ok").all()
    assert len(result) == 2


def test_universe_validation_sanitizes_invalid_ohlc_rows_before_signals() -> None:
    frame = _frame(80)
    frame.loc[frame.index[5], "High"] = float("inf")
    frame.loc[frame.index[6], "Low"] = 0.0
    result = evaluate_symbol_universe(
        {"AAA": frame},
        _frame(80)["Close"],
        min_train_size=10,
        n_splits=2,
        minimum_observations=30,
        cost_bps=0.0,
    )

    assert result["status"].eq("ok").all()
    assert len(result) == 2


def test_universe_validation_skips_when_benchmark_dates_do_not_align() -> None:
    frame = _frame(80)
    benchmark = pd.Series([100.0, 101.0], index=pd.date_range("2020-01-01", periods=2, freq="D"))
    result = evaluate_symbol_universe(
        {"AAA": frame},
        benchmark,
        min_train_size=10,
        n_splits=2,
        minimum_observations=30,
    )

    assert result.iloc[0]["symbol"] == "AAA"
    assert result.iloc[0]["status"] == "skipped"
    assert "benchmark has no observations aligned" in result.iloc[0]["reason"]
    assert result.iloc[0]["skip_category"] == "benchmark_data"


def test_universe_validation_excludes_inconsistent_ohlc_rows() -> None:
    frame = _frame(80)
    frame.loc[frame.index[5], "High"] = frame.loc[frame.index[5], "Close"] - 1.0
    frame.loc[frame.index[6], "Low"] = frame.loc[frame.index[6], "Close"] + 1.0
    result = evaluate_symbol_universe(
        {"AAA": frame},
        _frame(80)["Close"],
        min_train_size=10,
        n_splits=2,
        minimum_observations=30,
        cost_bps=0.0,
    )

    assert result["status"].eq("ok").all()
    assert len(result) == 2


def test_universe_validation_excludes_open_outside_ohlc_range() -> None:
    frame = _frame(80)
    frame["Open"] = frame["Close"]
    frame.loc[frame.index[5], "Open"] = frame.loc[frame.index[5], "High"] + 1.0
    frame.loc[frame.index[6], "Open"] = frame.loc[frame.index[6], "Low"] - 1.0
    result = evaluate_symbol_universe(
        {"AAA": frame},
        _frame(80)["Close"],
        min_train_size=10,
        n_splits=2,
        minimum_observations=30,
        cost_bps=0.0,
    )

    assert result["status"].eq("ok").all()
    assert len(result) == 2


def test_universe_validation_skips_duplicate_price_timestamps() -> None:
    frame = _frame(80)
    frame = pd.concat([frame, frame.iloc[[10]]])
    result = evaluate_symbol_universe(
        {"AAA": frame},
        _frame(80)["Close"],
        min_train_size=10,
        n_splits=2,
        minimum_observations=30,
    )

    assert result.iloc[0]["symbol"] == "AAA"
    assert result.iloc[0]["status"] == "skipped"
    assert "duplicate price timestamps" in result.iloc[0]["reason"]


def test_universe_validation_sorts_unordered_price_timestamps() -> None:
    frame = _frame(80).sample(frac=1.0, random_state=7)
    result = evaluate_symbol_universe(
        {"AAA": frame},
        _frame(80)["Close"],
        min_train_size=10,
        n_splits=2,
        minimum_observations=30,
        cost_bps=0.0,
    )

    assert result["status"].eq("ok").all()
    assert len(result) == 2


def test_universe_validation_rejects_duplicate_benchmark_timestamps() -> None:
    frame = _frame(80)
    benchmark = pd.concat([frame["Close"], frame["Close"].iloc[[10]]])
    try:
        evaluate_symbol_universe(
            {"AAA": frame},
            benchmark,
            min_train_size=10,
            n_splits=2,
            minimum_observations=30,
        )
    except ValueError as exc:
        assert "benchmark contains duplicate timestamps" in str(exc)
    else:
        raise AssertionError("expected duplicate benchmark timestamps to be rejected")


def test_universe_validation_sorts_benchmark_timestamps() -> None:
    frame = _frame(80)
    benchmark = frame["Close"].sample(frac=1.0, random_state=11)
    result = evaluate_symbol_universe(
        {"AAA": frame},
        benchmark,
        min_train_size=10,
        n_splits=2,
        minimum_observations=30,
        cost_bps=0.0,
    )

    assert result["status"].eq("ok").all()
    assert len(result) == 2


def test_universe_validation_categorizes_invalid_price_timestamps() -> None:
    frame = _frame(80)
    frame = pd.concat([frame, frame.iloc[[10]]])
    result = evaluate_symbol_universe(
        {"AAA": frame},
        _frame(80)["Close"],
        min_train_size=10,
        n_splits=2,
        minimum_observations=30,
    )

    assert result.iloc[0]["status"] == "skipped"
    assert result.iloc[0]["skip_category"] == "invalid_price_data"
