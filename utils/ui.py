import streamlit as st


def section(title):
    st.subheader(title)


def card(title, value, delta=None):
    st.metric(label=title, value=value, delta=delta)


def recommendation_box(action, confidence, risk):

    if "BUY" in action.upper():
        st.success(action)

    elif "SELL" in action.upper():
        st.error(action)

    else:
        st.warning(action)

    col1, col2 = st.columns(2)

    col1.metric("Confidence", f"{confidence}%")
    col2.metric("Risk", risk)


def show_reasons(reasons):

    if not reasons:
        return

    st.markdown("### Reasons")

    for reason in reasons:
        st.write(f"✅ {reason}")
