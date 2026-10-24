"""Interactive, research-only Gann–Fibonacci time/price dashboard."""

from __future__ import annotations

import math
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules.gann_fibonacci_time import (
    detect_confirmed_pivots,
    project_gann_fan,
    project_time_zones,
    validate_ohlcv,
)
from modules.gann_fibonacci_time.confluence import eligible_time_zone_indices, find_confluence

st.set_page_config(page_title="Gann–Fibonacci Time & Price Lab", page_icon="🧭", layout="wide")
st.title("🧭 Gann–Fibonacci Time & Price Research Lab")
st.caption(
    "Historical analysis and configurable projections. Historical confluence is evaluated only "
    "at or after the anchor confirmation bar. This page does not submit broker orders or provide "
    "trade recommendations."
)
st.warning(
    "Gann scales and time-zone intervals are research hypotheses, not proven predictive signals. "
    "Projections depend on the chosen anchor and price-per-bar scale. Validate any hypothesis "
    "out of sample before considering trading use."
)

with st.expander("CSV format and methodology", expanded=True):
    st.markdown(
        "Upload chronological OHLC data with **timestamp, open, high, low, close** columns. "
        "The dashboard validates candle order and OHLC relationships. Confirmed pivots are only "
        "known after the configured right-side bars have closed; the confirmation index is shown "
        "separately from the historical pivot index."
    )
    st.caption(
        "The default time intervals (3, 5, 8, 11, 21, 34) count rows/trading bars, not calendar days. "
        "The price-per-bar scale is an explicit input; a chart's visual 45° angle is not universal."
    )

# Android document providers may report downloaded .csv files with a generic MIME
# type. Avoid filtering in the native picker and validate the selected file below.
uploaded = st.file_uploader("Upload historical OHLC CSV", type=None)
if uploaded is None:
    st.info("Upload a CSV to inspect time zones, confirmed pivots, and Gann Fan projections.")
    st.stop()

try:
    frame = pd.read_csv(BytesIO(uploaded.getvalue()))
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    frame = validate_ohlcv(frame)
except (UnicodeDecodeError, pd.errors.ParserError, TypeError, ValueError) as exc:
    st.error(f"Unable to validate this file: {exc}")
    st.stop()

if len(frame) < 5:
    st.error("Upload at least five valid candles. More history is recommended for pivot analysis.")
    st.stop()

st.caption(
    f"Validated {len(frame):,} candles · {frame['timestamp'].iloc[0]} to "
    f"{frame['timestamp'].iloc[-1]} · no live data is requested by this page."
)

left, middle, right = st.columns(3)
with left:
    left_bars = st.number_input("Pivot left bars", min_value=1, max_value=20, value=3, step=1)
with middle:
    right_bars = st.number_input(
        "Pivot confirmation bars", min_value=1, max_value=20, value=3, step=1
    )
with right:
    tolerance_pct = st.number_input(
        "Confluence tolerance (%)", min_value=0.0, max_value=10.0, value=0.5, step=0.1
    )

try:
    pivots = detect_confirmed_pivots(frame, left_bars=int(left_bars), right_bars=int(right_bars))
except ValueError as exc:
    st.error(f"Could not detect pivots: {exc}")
    st.stop()

if pivots:
    pivot_labels = [
        (
            f"{item['kind'].title()} · bar {item['pivot_index']} "
            f"(confirmed at {item['confirmed_at_index']}) · {item['price']:.2f}"
        )
        for item in pivots
    ]
    selected = st.selectbox(
        "Anchor pivot",
        options=list(range(len(pivots))),
        format_func=lambda index: pivot_labels[index],
        help="A pivot is only available after its confirmation bars have elapsed.",
    )
    anchor = pivots[selected]
    anchor_index = int(anchor["pivot_index"])
    anchor_confirmation_index = int(anchor["confirmed_at_index"])
    anchor_price = float(anchor["price"])
    default_direction = 1 if anchor["kind"] == "low" else -1
else:
    st.info("No strict pivots found with these settings. Choose an anchor manually.")
    anchor_index = int(
        st.number_input(
            "Anchor bar index", min_value=0, max_value=len(frame) - 1, value=len(frame) // 2
        )
    )
    anchor_price = float(
        st.number_input(
            "Anchor price",
            min_value=0.01,
            value=float(frame.loc[anchor_index, "close"]),
            step=0.5,
        )
    )
    anchor_confirmation_index = anchor_index
    default_direction = 1

controls_left, controls_middle, controls_right = st.columns(3)
with controls_left:
    direction_label = st.radio(
        "Projection direction",
        ("Up", "Down"),
        index=0 if default_direction == 1 else 1,
        horizontal=True,
    )
with controls_middle:
    price_per_bar = st.number_input(
        "Price units per bar (ratio 1.0)",
        min_value=0.01,
        value=max(float(frame["close"].iloc[-1]) * 0.01, 0.01),
        step=0.5,
        help="An explicit research scale, not an automatically inferred universal Gann angle.",
    )
with controls_right:
    horizon = st.selectbox("Projection horizon (bars)", options=(8, 21, 34, 55), index=2)

direction = 1 if direction_label == "Up" else -1
intervals = (3, 5, 8, 11, 21, 34)
time_zones = project_time_zones(
    anchor_index, max(len(frame), anchor_index + int(horizon) + 1), intervals
)
target_indices = list(range(anchor_index, anchor_index + int(horizon) + 1))
ratios = (0.25, 1.0, 2.0, 3.0, 4.0)
projections = project_gann_fan(
    anchor_index,
    anchor_price,
    target_indices,
    price_per_bar=float(price_per_bar),
    direction=direction,
    ratios=ratios,
)

observed_prices = {index: float(value) for index, value in enumerate(frame["close"].tolist())}
historical_zones = eligible_time_zone_indices(
    [item["bar_index"] for item in time_zones],
    confirmed_at_index=anchor_confirmation_index,
    total_bars=len(frame),
)
historical_projections = [item for item in projections if int(item["target_index"]) < len(frame)]
try:
    confluence = find_confluence(
        historical_zones,
        historical_projections,
        observed_prices,
        tolerance_pct=float(tolerance_pct),
    )
except (KeyError, TypeError, ValueError) as exc:
    st.error(f"Could not calculate historical confluence: {exc}")
    st.stop()

# Historical prices and forward projections use separate axes. Mixing future
# fan lines into the full history chart can stretch the price axis and hide detail.
history_fig = go.Figure()
history_fig.add_trace(
    go.Scatter(
        x=list(range(len(frame))),
        y=frame["close"],
        mode="lines",
        name="Historical close",
        line={"width": 2},
    )
)
history_fig.add_trace(
    go.Scatter(
        x=[anchor_index],
        y=[anchor_price],
        mode="markers",
        name="Selected anchor",
        marker={"size": 11, "symbol": "diamond"},
    )
)
for zone in time_zones:
    index = int(zone["bar_index"])
    if index < len(frame):
        history_fig.add_vline(x=index, line_dash="dot", opacity=0.25)
close_min = float(frame["close"].min())
close_max = float(frame["close"].max())
close_padding = max((close_max - close_min) * 0.08, abs(close_max) * 0.01, 0.01)
history_fig.update_layout(
    height=420,
    template="plotly_white",
    xaxis_title="Bar index (trading rows)",
    yaxis_title="Historical close price",
    legend_title="Series",
    margin={"l": 12, "r": 12, "t": 28, "b": 28},
    yaxis={"range": [close_min - close_padding, close_max + close_padding]},
)
st.plotly_chart(history_fig, use_container_width=True)

with st.expander("Gann price projection chart (zoomed)", expanded=True):
    projection_fig = go.Figure()
    projection_fig.add_hline(
        y=anchor_price,
        line_dash="dot",
        opacity=0.7,
        annotation_text=f"Anchor {anchor_price:.2f}",
    )
    for ratio in ratios:
        ratio_rows = [
            item
            for item in projections
            if math.isclose(float(item["ratio"]), ratio, rel_tol=0.0, abs_tol=1e-9)
        ]
        projection_fig.add_trace(
            go.Scatter(
                x=[int(item["target_index"]) for item in ratio_rows],
                # Non-positive equity prices are mathematical extensions, not
                # feasible chart targets. Break the line at those points so they
                # cannot stretch the mobile chart's price axis below zero.
                y=[
                    float(item["price"]) if float(item["price"]) > 0 else None
                    for item in ratio_rows
                ],
                mode="lines+markers",
                name=f"Gann ratio {ratio:g}",
            )
        )
    positive_projection_prices = [
        float(item["price"]) for item in projections if float(item["price"]) > 0
    ]
    if positive_projection_prices:
        projection_min = min(positive_projection_prices)
        projection_max = max(positive_projection_prices)
        projection_padding = max(
            (projection_max - projection_min) * 0.08,
            abs(projection_max) * 0.02,
            0.01,
        )
        projection_fig.update_yaxes(
            range=[
                max(0.0, projection_min - projection_padding),
                projection_max + projection_padding,
            ]
        )
    projection_fig.update_layout(
        height=380,
        template="plotly_white",
        xaxis_title="Target bar index",
        yaxis_title="Projected price (positive levels)",
        legend_title="Gann ratio",
        margin={"l": 12, "r": 12, "t": 28, "b": 28},
        xaxis={"range": [anchor_index, anchor_index + int(horizon)]},
    )
    st.plotly_chart(projection_fig, use_container_width=True)
    non_positive_count = sum(float(item["price"]) <= 0 for item in projections)
    if non_positive_count:
        st.caption(
            f"{non_positive_count} non-positive projection point(s) are omitted from this chart "
            "because they are not feasible equity prices. Their calculated values remain available "
            "in the numerical projection section below."
        )

with st.expander("Numerical Gann price projections", expanded=True):
    projection_rows = [
        {
            "Target bar": int(item["target_index"]),
            "Bars from anchor": int(item["target_index"]) - anchor_index,
            "Gann ratio": float(item["ratio"]),
            "Projected price": round(float(item["price"]), 2),
            "Price status": (
                "Positive"
                if float(item["price"]) > 0
                else "Non-positive; not a feasible equity price"
            ),
            "Direction": item["direction"].title(),
        }
        for item in projections
        if (
            int(item["target_index"])
            in {anchor_index + interval for interval in intervals if interval <= int(horizon)}
            or int(item["target_index"]) == anchor_index + int(horizon)
        )
    ]
    projection_frame = pd.DataFrame(projection_rows)
    if projection_frame.empty:
        st.info("No projection levels fall within the selected horizon.")
    else:
        # Group ratios by target bar so prices remain readable on narrow screens.
        for target_bar, target_rows in projection_frame.groupby("Target bar", sort=True):
            bars_from_anchor = int(target_rows["Bars from anchor"].iloc[0])
            st.markdown(f"**Target bar {target_bar}** · {bars_from_anchor} bars from anchor")
            price_items = [
                f"{row['Gann ratio']:g}×: {row['Projected price']:.2f}"
                for _, row in target_rows.sort_values("Gann ratio").iterrows()
            ]
            st.write(" · ".join(price_items))
            if (target_rows["Price status"] != "Positive").any():
                st.caption(
                    "Warning: one or more levels are non-positive and are not feasible equity prices."
                )
    if any(float(item["price"]) <= 0 for item in projections):
        st.warning(
            "Some linear projections reach zero or negative prices. These are mathematical "
            "extensions of the selected scale, not feasible equity-price targets; reconsider "
            "the scale or horizon before interpreting them."
        )
    st.caption(
        "Calculation: anchor price + direction × bars from anchor × price units per bar × Gann ratio. "
        "Changing Up/Down reverses the sign of the price change; time-zone bars do not change."
    )

metric_left, metric_middle, metric_right = st.columns(3)
metric_left.metric("Confirmed pivots", f"{len(pivots):,}")
metric_middle.metric("Projected time zones", f"{len(time_zones):,}")
metric_right.metric("Historical confluence matches", f"{len(confluence):,}")

with st.expander("Projected Fibonacci time zones", expanded=True):
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Interval (bars)": item["interval"],
                    "Projected bar index": item["bar_index"],
                    "Status": (
                        "Historical" if item["bar_index"] < len(frame) else "Future projection"
                    ),
                }
                for item in time_zones
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

with st.expander("Confirmed pivot audit trail"):
    if pivots:
        pivot_frame = pd.DataFrame(pivots)
        pivot_frame["pivot_timestamp"] = pivot_frame["pivot_index"].map(
            lambda index: frame.loc[index, "timestamp"]
        )
        pivot_frame["confirmation_timestamp"] = pivot_frame["confirmed_at_index"].map(
            lambda index: frame.loc[index, "timestamp"]
        )
        st.dataframe(pivot_frame, use_container_width=True, hide_index=True)
    else:
        st.write("No pivots detected for the selected confirmation window.")

with st.expander("Historical time–price confluence matches"):
    if confluence:
        st.dataframe(pd.DataFrame(confluence), use_container_width=True, hide_index=True)
    else:
        st.write(
            "No historical matches found at the selected tolerance. Future projected bars cannot "
            "be counted as confirmed confluence because future observed prices are not available."
        )

st.caption(
    "Research-only: a confluence match is a geometric proximity condition, not a buy/sell signal. "
    "This dashboard does not establish profitability and does not place orders."
)
