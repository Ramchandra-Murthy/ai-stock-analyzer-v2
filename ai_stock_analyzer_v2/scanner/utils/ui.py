import streamlit as st


def section(title):
    st.markdown(f"## {title}")


def card(title, value, delta=None):
    st.metric(label=title, value=value, delta=delta)


def recommendation_box(action, confidence, risk):

    if "BUY" in action:
        st.success(f"### {action}")

    elif "SELL" in action:
        st.error(f"### {action}")

    else:
        st.warning(f"### {action}")

    c1, c2 = st.columns(2)

    c1.metric("Confidence", f"{confidence}%")

    c2.metric("Risk", risk)


def show_reasons(reasons):

    st.write("### Reasons")

    for reason in reasons:

        st.write(f"✅ {reason}")
