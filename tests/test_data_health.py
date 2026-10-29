import pandas as pd

from services.data_health import (
    FAIL,
    PASS,
    WARN,
    Coverage,
    best_form,
    measure_coverage,
    verdict,
)

BAR = pd.DataFrame({"Close": [1.0, 2.0]})


def downloader_serving(available):
    def download(chunk, **kwargs):
        frames = {t: BAR for t in chunk if t in available}
        return frames, [t for t in chunk if t not in frames]

    return download


def test_counts_loaded_and_names_missing():
    cov = measure_coverage("BSE", ["a.bo", "B.BO", "c.bo"], downloader_serving({"A.BO", "B.BO"}))
    assert (cov.tested, cov.loaded) == (3, 2)
    assert cov.missing == ("C.BO",)
    assert cov.rate == 2 / 3


def test_empty_frames_do_not_count_as_loaded():
    def download(chunk, **kwargs):
        return {t: pd.DataFrame() for t in chunk}, []

    assert measure_coverage("x", ["A.BO"], download).loaded == 0


def test_a_crashing_chunk_does_not_hide_the_others():
    def download(chunk, **kwargs):
        if "BAD.BO" in chunk:
            raise RuntimeError("provider down")
        return {t: BAR for t in chunk}, []

    cov = measure_coverage("x", ["BAD.BO", "A.BO", "B.BO"], download, chunk_size=1)
    assert cov.loaded == 2 and cov.missing == ("BAD.BO",)


def test_duplicates_and_blanks_are_ignored():
    cov = measure_coverage("x", ["a.ns", "A.NS", " ", ""], downloader_serving({"A.NS"}))
    assert (cov.tested, cov.loaded) == (1, 1)


def test_verdict_thresholds():
    assert verdict(Coverage("x", 10, 8, ()))[0] == PASS
    assert verdict(Coverage("x", 10, 5, ()))[0] == WARN
    assert verdict(Coverage("x", 10, 1, ()))[0] == FAIL
    assert verdict(Coverage("x", 0, 0, ()))[0] == WARN


def test_best_form_needs_a_clear_winner():
    codes, names = Coverage("scrip codes", 10, 3, ()), Coverage("names", 10, 9, ())
    assert best_form([codes, names]) == "names"
    assert best_form([Coverage("a", 10, 8, ()), Coverage("b", 10, 9, ())]) is None
    assert best_form([codes]) is None
