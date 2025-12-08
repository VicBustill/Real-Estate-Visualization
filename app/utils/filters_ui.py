# app/utils/filters_ui.py
import streamlit as st

def render_sidebar_filters():
    """
    UI-only sidebar filters.
    Uses st.session_state keys so existing logic that reads them keeps working.
    Does NOT return anything and does NOT change your data logic.
    """

    with st.sidebar:
        st.markdown("## 🧭 Filters")

        st.markdown("### 📍 Location")
        st.text_input("📮 ZIP (optional)", key="zip_code")
        st.text_input("🗺️ Abbreviated State", key="state")
        st.text_input("🏙️ City", key="city")

        st.markdown("---")

        st.markdown("### 💰 Price Range")
        st.number_input(
            "Min price", min_value=0, step=50_000, key="min_price"
        )
        st.number_input(
            "Max price", min_value=0, value=2_000_000, step=50_000, key="max_price"
        )

        st.markdown("---")

        st.markdown("### 🛏️ Bedrooms")
        st.number_input(
            "Min beds", min_value=0, step=1, key="min_beds"
        )
        st.number_input(
            "Max beds (optional)", min_value=0, step=1, key="max_beds"
        )
