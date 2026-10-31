import threading
import time

import pandas as pd

from scanner.gainers import build_gainer_rows, coverage_message, download_with_fallback
from services.parallel_download import download_in_parallel


def _frame(closes, volumes=None):
    data = {"Close": closes}
    if volumes is not None:
        data["Volume"] = volumes
    return pd.DataFrame(data)


def test_gainers_sorted_and_names_bse_codes():
    daily = {
        "500325.BO": _frame([100.0, 102.0], [10, 20]),
        "532540.BO": _frame([200.0, 190.0]),
    }
    intraday = {"500325.BO": _frame([101.0, 105.0])}
    scan = build_gainer_rows(["532540.BO", "500325.BO"], intraday, daily, ".BO")
    assert [r["Symbol"] for r in scan.rows] == ["500325", "532540"]
    top = scan.rows[0]
    assert top["Company"] == "RELIANCE (BSE 500325)"
    assert top["Price"] == 105.0  # intraday last beats the daily close
    assert round(top["Change (%)"], 2) == 5.0
    assert top["Volume"] == 20
    assert scan.rows[1]["Volume"] is None
    assert scan.skipped == {}


def test_every_unscorable_symbol_is_accounted_for_with_a_reason():
    daily = {
        "AAA.BO": _frame([10.0]),
        "BBB.BO": _frame([0.0, 5.0]),
        "CCC.BO": pd.DataFrame({"Open": [1, 2]}),
        "DDD.BO": _frame([10.0, 11.0]),
    }
    scan = build_gainer_rows(["AAA.BO", "BBB.BO", "CCC.BO", "DDD.BO", "EEE.BO"], {}, daily, ".BO")
    assert [r["Ticker"] for r in scan.rows] == ["DDD.BO"]
    assert set(scan.skipped) == {"AAA.BO", "BBB.BO", "CCC.BO", "EEE.BO"}
    assert scan.scored + len(scan.skipped) == scan.candidates == 5
    message = coverage_message(scan, "BSE", 80)
    assert "Scored 1 of 5 BSE candidates" in message
    assert "4 returned no usable data" in message


def test_coverage_message_is_quiet_when_everything_scored():
    scan = build_gainer_rows(["X.BO"], {}, {"X.BO": _frame([1.0, 2.0])}, ".BO")
    assert "no usable data" not in coverage_message(scan, "BSE", 80)


def test_parallel_download_merges_chunks_and_reports_missing_in_order():
    def fake(chunk, **kwargs):
        frames = {t: _frame([1.0, 2.0]) for t in chunk if t != "BAD.BO"}
        return frames, [t for t in chunk if t not in frames]

    symbols = [f"S{i}.BO" for i in range(10)] + ["BAD.BO", "s1.bo"]
    frames, missing = download_in_parallel(fake, symbols, chunk_size=3, workers=4)
    assert len(frames) == 10  # duplicates (case-insensitive) collapse
    assert missing == ["BAD.BO"]


def test_one_failing_chunk_does_not_blank_the_rest():
    def flaky(chunk, **kwargs):
        if "S0.BO" in chunk:
            raise RuntimeError("provider timeout")
        return {t: _frame([1.0, 2.0]) for t in chunk}, []

    frames, missing = download_in_parallel(flaky, [f"S{i}.BO" for i in range(6)], chunk_size=2)
    assert sorted(frames) == ["S2.BO", "S3.BO", "S4.BO", "S5.BO"]
    assert missing == ["S0.BO", "S1.BO"]


def test_parallel_download_really_runs_chunks_concurrently_and_forwards_kwargs():
    seen, threads = {}, set()

    def slow(chunk, **kwargs):
        seen.update(kwargs)
        threads.add(threading.get_ident())
        time.sleep(0.2)
        return {t: _frame([1.0, 2.0]) for t in chunk}, []

    started = time.perf_counter()
    download_in_parallel(slow, [f"S{i}.BO" for i in range(8)], chunk_size=2, workers=4, period="5d")
    elapsed = time.perf_counter() - started
    assert seen == {"period": "5d"}
    assert len(threads) > 1
    assert elapsed < 0.6  # four chunks of 0.2s would take 0.8s serially


def test_parallel_download_empty_input():
    assert download_in_parallel(lambda c, **k: ({}, []), []) == ({}, [])


# --- name-form fallback ---------------------------------------------------------------------


def _serving(available):
    calls = []

    def download(chunk):
        calls.append(list(chunk))
        frames = {t: pd.DataFrame({"Close": [1.0, 2.0]}) for t in chunk if t in available}
        return frames, [t for t in chunk if t not in frames]

    return download, calls


def test_fallback_recovers_a_code_the_provider_does_not_serve():
    download, calls = _serving({"RELIANCE.BO", "532540.BO"})
    alternates = {"500325.BO": "RELIANCE.BO", "532540.BO": "TCS.BO"}
    frames = download_with_fallback(download, ["500325.BO", "532540.BO"], alternates)
    assert set(frames) == {"500325.BO", "532540.BO"}  # keyed by the ORIGINAL ticker
    assert calls == [["500325.BO", "532540.BO"], ["RELIANCE.BO"]]  # only the miss is retried


def test_fallback_not_used_when_everything_loads():
    download, calls = _serving({"500325.BO"})
    download_with_fallback(download, ["500325.BO"], {"500325.BO": "RELIANCE.BO"})
    assert len(calls) == 1


def test_fallback_gives_up_quietly_and_ignores_empty_frames():
    def download(chunk):
        return {t: pd.DataFrame() for t in chunk}, []

    frames = download_with_fallback(download, ["500325.BO"], {"500325.BO": "RELIANCE.BO"})
    assert frames == {}


def test_no_alternates_means_no_second_download():
    download, calls = _serving(set())
    assert download_with_fallback(download, ["TCS.NS"], {}) == {}
    assert len(calls) == 1


def test_prefer_alternate_asks_name_first_and_keeps_original_keys():
    import pandas as pd

    from scanner.gainers import download_with_fallback

    asked = []

    def download(batch):
        asked.append(list(batch))
        return {
            t: pd.DataFrame({"Close": [1.0, 2.0]}) for t in batch if t.endswith("RELIANCE.BO")
        }, []

    frames = download_with_fallback(
        download, ["500325.BO"], {"500325.BO": "RELIANCE.BO"}, prefer_alternate=True
    )
    assert asked == [["RELIANCE.BO"]]  # one round trip
    assert list(frames) == ["500325.BO"]
