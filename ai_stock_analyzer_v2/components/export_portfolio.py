import streamlit as st


def export_portfolio(df):
    """Display a button to download the portfolio as a CSV file.

    CSV uses pandas' built-in export and avoids an optional Excel dependency
    during application startup on hosts that install from uv.lock.
    """
    if df.empty:
        return

    csv_data = df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="📥 Download Portfolio (CSV)",
        data=csv_data,
        file_name="portfolio.csv",
        mime="text/csv",
        use_container_width=True,
    )
