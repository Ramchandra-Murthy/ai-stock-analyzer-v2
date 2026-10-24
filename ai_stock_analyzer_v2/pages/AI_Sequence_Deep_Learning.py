"""AI sequence/deep-learning research dashboard."""

# ruff: noqa: I001

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.sequence_model import predict_sequence, train_sequence_model

st.title("AI Sequence / Deep Learning")
st.caption("Research-only sequence model with chronological validation; no live orders.")

symbol = st.text_input("Symbol", "RELIANCE.NS")
sequence_length = st.slider("Sequence length", 5, 40, 20)
horizon = st.slider("Prediction horizon", 1, 20, 5)
threshold = st.number_input("Return threshold", value=0.0, step=0.001)
close_text = st.text_area("Close prices", height=120)
volume_text = st.text_area("Volumes", height=120)

if st.button("Run Sequence Validation"):
    try:
        close = [float(value.strip()) for value in close_text.split(",") if value.strip()]
        volume = [float(value.strip()) for value in volume_text.split(",") if value.strip()]
        if len(close) != len(volume):
            raise ValueError("Close and volume lengths must match")
        frame = pd.DataFrame({"Close": close, "Volume": volume})
        trained, validation = train_sequence_model(
            frame,
            sequence_length=sequence_length,
            horizon=horizon,
            threshold=threshold,
        )
        prediction = predict_sequence(
            trained,
            frame,
            sequence_length=sequence_length,
        )
        st.success(f"{symbol}: {prediction['signal']}")
        st.metric("Probability Up", f"{prediction['probability_up']:.1%}")
        st.metric("Confidence", f"{prediction['confidence']:.1%}")
        st.metric("Validation Accuracy", f"{validation.accuracy:.1%}")
        st.metric(
            "ROC-AUC",
            "N/A" if validation.roc_auc is None else f"{validation.roc_auc:.3f}",
        )
        st.caption(
            f"Chronological train/test samples: {validation.train_samples} / "
            f"{validation.test_samples}"
        )
    except ValueError as exc:
        st.error(str(exc))
