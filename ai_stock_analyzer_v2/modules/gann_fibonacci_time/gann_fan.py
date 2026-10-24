"""Gann Fan projections with an explicit price-per-bar scale."""

DEFAULT_RATIOS = (0.25, 1.0, 2.0, 3.0, 4.0)


def project_gann_fan(
    anchor_index: int,
    anchor_price: float,
    target_indices: list[int] | tuple[int, ...],
    price_per_bar: float,
    direction: int = 1,
    ratios: tuple[float, ...] = DEFAULT_RATIOS,
) -> list[dict[str, int | float | str]]:
    """Project levels; ratio 1.0 means price_per_bar units per bar."""
    if isinstance(anchor_index, bool) or not isinstance(anchor_index, int) or anchor_index < 0:
        raise ValueError("anchor_index must be a non-negative integer.")
    if not isinstance(anchor_price, (int, float)) or not 0 < anchor_price < float("inf"):
        raise ValueError("anchor_price must be finite and positive.")
    if not isinstance(price_per_bar, (int, float)) or not 0 < price_per_bar < float("inf"):
        raise ValueError("price_per_bar must be finite and positive.")
    if direction not in (-1, 1):
        raise ValueError("direction must be -1 or 1.")
    if not ratios or any(
        not isinstance(ratio, (int, float)) or ratio <= 0 or ratio == float("inf")
        for ratio in ratios
    ):
        raise ValueError("ratios must be finite positive numbers.")
    if any(
        isinstance(index, bool) or not isinstance(index, int) or index < anchor_index
        for index in target_indices
    ):
        raise ValueError("Target indices must be integers at or after the anchor.")
    projections = []
    for index in sorted(set(target_indices)):
        elapsed = index - anchor_index
        for ratio in sorted({float(value) for value in ratios}):
            price = float(anchor_price) + direction * elapsed * float(price_per_bar) * ratio
            projections.append(
                {
                    "target_index": index,
                    "ratio": ratio,
                    "price": price,
                    "direction": "up" if direction == 1 else "down",
                }
            )
    return projections
