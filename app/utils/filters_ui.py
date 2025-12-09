import streamlit as st

def render_sidebar_filters():
    """
    Shared sidebar filters for all pages.

    - Stores values in st.session_state so pages can read them.
    - Returns True when the user clicks "Search listings".
    """

    with st.sidebar:
        st.markdown("## 🧭 Filters")

        # --- Controls at the top ---
        search_clicked = st.button("🔍 Search listings", use_container_width=True)

        if st.button("♻️ Reset Filters", use_container_width=True):
            # Reset filters to defaults
            st.session_state["zip_code"] = ""
            st.session_state["state"] = ""
            st.session_state["city"] = ""
            st.session_state["min_price"] = 0
            st.session_state["max_price"] = 2_000_000
            st.session_state["min_beds"] = 0
            st.session_state["max_beds"] = 0
            st.session_state["property_type_options"] = []
            st.session_state["status_option"] = "Any"
            st.session_state["min_year"] = 0
            st.session_state["max_year"] = 0
            st.session_state["min_sqft"] = 0
            st.session_state["max_sqft"] = 0
            st.session_state["min_ppsqft"] = 0
            st.session_state["max_ppsqft"] = 0

            # 🔁 tell all pages "a reset just happened"
            st.session_state["reset_filters_flag"] = True

            # 🔁 force immediate rerun so UI + data refresh
            try:
                st.rerun()
            except Exception:
                st.experimental_rerun()

        st.markdown("---")

        # --- Location ---
        st.markdown("### 📍 Location")
        st.text_input("📮 ZIP (optional)", key="zip_code")
        st.text_input("🗺️ Abbreviated State", key="state")
        st.text_input("🏙️ City", key="city")

        st.markdown("---")

        # --- Price ---
        st.markdown("### 💰 Price Range")
        st.number_input(
            "Min price", min_value=0, step=50_000, key="min_price"
        )
        st.number_input(
            "Max price", min_value=0, value=2_000_000, step=50_000, key="max_price"
        )

        st.markdown("---")

        # --- Bedrooms ---
        st.markdown("### 🛏️ Bedrooms")
        st.number_input(
            "Min beds", min_value=0, step=1, key="min_beds"
        )
        st.number_input(
            "Max beds (optional)", min_value=0, step=1, key="max_beds"
        )

        st.markdown("---")

        # --- Extra property filters ---
        st.markdown("### 🏡 Property Details")

        st.multiselect(
            "Property type",
            options=["Single Family", "Condo", "Townhouse", "Multi-Family", "Apartment"],
            key="property_type_options",
        )

        st.selectbox(
            "Status",
            options=["Any", "Active", "Inactive", "Sold"],
            index=0,
            key="status_option",
        )

        st.number_input(
            "Min year built", min_value=0, value=0, step=5, key="min_year"
        )
        st.number_input(
            "Max year built", min_value=0, value=0, step=5, key="max_year"
        )

        st.number_input(
            "Min square footage", min_value=0, value=0, step=100, key="min_sqft"
        )
        st.number_input(
            "Max square footage", min_value=0, value=0, step=100, key="max_sqft"
        )

        st.number_input(
            "Min price per sq ft", min_value=0, value=0, step=50, key="min_ppsqft"
        )
        st.number_input(
            "Max price per sq ft", min_value=0, value=0, step=50, key="max_ppsqft"
        )

    return search_clicked
