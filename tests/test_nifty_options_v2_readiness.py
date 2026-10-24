from engine.nifty_options_v2_readiness import automatic_cycle_ready


def test_automatic_cycle_is_ready_only_when_all_safety_gates_pass() -> None:
    readiness = automatic_cycle_ready(
        provider_ready=True,
        market_session_ready=True,
        market_data_fresh=True,
    )

    assert readiness.ready


def test_automatic_cycle_is_blocked_when_provider_is_unavailable() -> None:
    readiness = automatic_cycle_ready(
        provider_ready=False,
        market_session_ready=True,
        market_data_fresh=True,
    )

    assert not readiness.ready


def test_automatic_cycle_is_blocked_outside_market_session() -> None:
    readiness = automatic_cycle_ready(
        provider_ready=True,
        market_session_ready=False,
        market_data_fresh=True,
    )

    assert not readiness.ready


def test_automatic_cycle_is_blocked_when_market_data_is_stale() -> None:
    readiness = automatic_cycle_ready(
        provider_ready=True,
        market_session_ready=True,
        market_data_fresh=False,
    )

    assert not readiness.ready
