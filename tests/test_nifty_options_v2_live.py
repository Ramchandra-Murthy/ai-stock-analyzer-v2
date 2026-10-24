from datetime import date

import pytest

from engine.nifty_options_v2_live import (
    LivePaperObservation,
    NiftyOptionsV2LivePaperSession,
)


def test_live_paper_session_starts_and_closes() -> None:
    session = NiftyOptionsV2LivePaperSession()
    entry = LivePaperObservation(date(2026, 10, 5), 25000, 500)
    exit_observation = LivePaperObservation(date(2026, 10, 29), 25500, 650)

    session.start(expiry=date(2026, 10, 29), strike=24500, observation=entry)
    closed = session.close(exit_observation)

    assert closed.points_pnl == 150
    assert len(session.trader.completed_trades) == 1


def test_live_paper_session_rejects_non_itm_start() -> None:
    session = NiftyOptionsV2LivePaperSession()

    with pytest.raises(ValueError, match="ITM CALL"):
        session.start(
            expiry=date(2026, 10, 29),
            strike=25000,
            observation=LivePaperObservation(date(2026, 10, 5), 25000, 500),
        )
