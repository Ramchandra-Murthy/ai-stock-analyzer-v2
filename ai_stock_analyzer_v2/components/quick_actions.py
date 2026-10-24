import streamlit as st


def show_quick_actions():
    """
    Professional Quick Action Toolbar
    """

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    with col2:
        if st.button("➕ Add Holding", use_container_width=True):
            st.info("Use the 'Add New Holding' section below.")

    with col3:
        if st.button("📤 Export", use_container_width=True):
            st.info("Use the Export Portfolio panel.")
