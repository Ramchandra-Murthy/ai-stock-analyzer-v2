"""Close-confirmed stop protection for research backtests.

This is a signal transformation, not an intrabar stop-order simulator. A stop
observed at a bar close changes the target signal at that close; the existing
backtester applies that change on the following bar.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def apply_close_stop(
    prices: pd.Series,
    signals: pd.Series,
    stop_loss_fraction: float,
) -> pd.Series:
    """Return target signals with a close-confirmed per-trade stop.

    A long position exits when close-to-entry loss reaches the stop fraction;
    a short position exits when the close-to-entry move reaches that loss.
    After a stop, new positions are suppressed until the original signal
    returns to zero, preventing immediate re-entry from a persistent signal.

    Signals are applied by the backtester on the next bar. Therefore this
    models a close-confirmed exit with next-bar execution, not a guaranteed
    stop fill at the threshold. Input indices must be unique and are aligned
    and sorted by timestamp.
    """
    if not np.isfinite(stop_loss_fraction) or not 0.0 < stop_loss_fraction < 1.0:
        raise ValueError("stop_loss_fraction must be finite and between zero and one")

    if not prices.index.is_unique or not signals.index.is_unique:
        raise ValueError("prices and signals must not contain duplicate timestamps")

    index = prices.index.intersection(signals.index).sort_values()
    if len(index) < 2:
        raise ValueError("at least two aligned observations are required")

    aligned_prices = pd.to_numeric(prices.reindex(index), errors="coerce")
    aligned_signals = pd.to_numeric(signals.reindex(index), errors="coerce")
    if not np.isfinite(aligned_prices.to_numpy()).all() or aligned_prices.le(0).any():
        raise ValueError("prices must be finite and greater than zero")
    if not np.isfinite(aligned_signals.to_numpy()).all():
        raise ValueError("signals must be finite")

    aligned_signals = aligned_signals.clip(-1.0, 1.0)
    output = aligned_signals.copy()

    def is_flat(position: float) -> bool:
        """Treat numerical noise around zero as a flat target position."""
        return bool(np.isclose(position, 0.0, rtol=0.0, atol=1e-12))

    active_position = 0.0
    entry_price: float | None = None
    stopped = False

    for i, timestamp in enumerate(index):
        desired = float(aligned_signals.loc[timestamp])
        price = float(aligned_prices.loc[timestamp])

        if stopped:
            output.loc[timestamp] = 0.0
            if is_flat(desired):
                stopped = False
            continue

        # Signals are executed on the next bar. Track the position currently
        # active at this close, based on the previous bar's original signal.
        if i > 0:
            previous_timestamp = index[i - 1]
            executed = float(output.loc[previous_timestamp])
            if not np.isclose(executed, active_position, rtol=0.0, atol=1e-12):
                active_position = executed
                entry_price = (
                    float(aligned_prices.loc[previous_timestamp]) if not is_flat(executed) else None
                )

        if is_flat(active_position) or entry_price is None:
            continue

        trade_return = active_position * (price / entry_price - 1.0)
        if trade_return <= -stop_loss_fraction:
            output.loc[timestamp] = 0.0
            stopped = True
            active_position = 0.0
            entry_price = None

    return output
