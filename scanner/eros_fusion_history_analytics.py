"""EROS fusion history analytics helpers."""

import pandas as pd  # noqa: I001

REQUIRED_HISTORY_COLUMNS = {"Timestamp", "Symbol", "Exchange", "Fusion Score"}


def prepare_eros_fusion_history(
    history: pd.DataFrame | None,
) -> pd.DataFrame:
    """Validate and normalize EROS fusion history for downstream analytics."""
    if history is None or history.empty:
        return pd.DataFrame()

    if not REQUIRED_HISTORY_COLUMNS.issubset(history.columns):
        return pd.DataFrame()

    frame = history.copy()
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    frame["Fusion Score"] = pd.to_numeric(frame["Fusion Score"], errors="coerce")
    frame = frame.dropna(subset=["Timestamp", "Fusion Score"])
    return frame.reset_index(drop=True)


def summarize_eros_fusion_history(
    history: pd.DataFrame | None,
) -> pd.DataFrame:
    """Summarize repeated EROS fusion observations by symbol and exchange."""
    frame = prepare_eros_fusion_history(history)
    if frame.empty:
        return pd.DataFrame()

    summary = (
        frame.groupby(["Symbol", "Exchange"], as_index=False)
        .agg(
            Observations=("Symbol", "size"),
            Average_Fusion=("Fusion Score", "mean"),
            Peak_Fusion=("Fusion Score", "max"),
            Latest_Fusion=("Fusion Score", "last"),
            First_Seen=("Timestamp", "min"),
            Last_Seen=("Timestamp", "max"),
        )
        .sort_values(
            ["Latest_Fusion", "Observations", "Average_Fusion"],
            ascending=[False, False, False],
        )
        .reset_index(drop=True)
    )
    summary["Persistence"] = pd.cut(
        summary["Observations"],
        bins=[0, 1, 2, 4, float("inf")],
        labels=["ONE", "REPEATED", "PERSISTENT", "HIGH PERSISTENCE"],
    )
    return summary
