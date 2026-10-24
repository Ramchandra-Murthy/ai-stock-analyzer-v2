"""Book-aligned drawdown-period diagnostics for research backtests."""

from __future__ import annotations

import pandas as pd


def drawdown_periods(
    returns: pd.Series,
    *,
    top: int = 5,
) -> pd.DataFrame:
    """Return the deepest drawdown periods with peak, valley, recovery, and duration."""
    if top < 1:
        raise ValueError("top must be at least 1")

    clean_returns = pd.to_numeric(returns, errors="coerce").dropna()
    columns = [
        "drawdown",
        "peak",
        "valley",
        "recovery",
        "duration",
    ]
    if clean_returns.empty:
        return pd.DataFrame(columns=columns)

    cumulative = (1.0 + clean_returns).cumprod()
    running_max = cumulative.cummax()
    underwater = cumulative / running_max - 1.0
    in_drawdown = underwater.lt(0.0)
    groups = in_drawdown.astype(int).diff().fillna(in_drawdown.iloc[0]).ne(0).cumsum()

    rows: list[dict[str, object]] = []
    for _, period in underwater[in_drawdown].groupby(groups[in_drawdown]):
        start_position = clean_returns.index.get_loc(period.index[0])
        peak_position = max(start_position - 1, 0)
        end_position = clean_returns.index.get_loc(period.index[-1]) + 1
        recovery = (
            clean_returns.index[end_position] if end_position < len(clean_returns.index) else None
        )
        rows.append(
            {
                "drawdown": float(period.min()),
                "peak": clean_returns.index[peak_position],
                "valley": period.idxmin(),
                "recovery": recovery,
                "duration": int(
                    (end_position if recovery is not None else len(clean_returns.index))
                    - peak_position
                ),
            }
        )

    if not rows:
        return pd.DataFrame(columns=columns)

    report = pd.DataFrame(rows).sort_values("drawdown").head(top).reset_index(drop=True)
    return report[columns]
