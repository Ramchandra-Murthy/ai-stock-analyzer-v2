"""Fibonacci time-zone projections measured in trading bars."""

DEFAULT_INTERVALS = (3, 5, 8, 11, 21, 34)


def project_time_zones(
    anchor_index: int, total_bars: int, intervals: tuple[int, ...] = DEFAULT_INTERVALS
) -> list[dict[str, int]]:
    """Return future bar indices for intervals that fit inside the data."""
    if isinstance(anchor_index, bool) or not isinstance(anchor_index, int) or anchor_index < 0:
        raise ValueError("anchor_index must be a non-negative integer.")
    if isinstance(total_bars, bool) or not isinstance(total_bars, int) or total_bars < 1:
        raise ValueError("total_bars must be a positive integer.")
    if anchor_index >= total_bars:
        raise ValueError("anchor_index must be within the available data.")
    if not intervals:
        raise ValueError("At least one time interval is required.")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in intervals
    ):
        raise ValueError("Time intervals must be positive integers.")
    return [
        {"interval": interval, "bar_index": anchor_index + interval}
        for interval in sorted(set(intervals))
        if anchor_index + interval < total_bars
    ]
