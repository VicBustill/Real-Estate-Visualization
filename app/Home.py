import os
import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import pydeck as pdk  # type: ignore
from utils.io import load_first_csv
from utils.style import apply_theme
from rentCast_collectionV2 import fetch_listings, save_listings_to_csv
from utils.filters_ui import render_sidebar_filters


# -----------------------------------------------------------
# 1️⃣ PAGE CONFIG + GLOBAL UI STYLING
# -----------------------------------------------------------

st.set_page_config(
    page_title="Real_Estate_Visualization",
    page_icon="🏠",
    layout="wide",
)

apply_theme()


# -----------------------------------------------------------
# 2️⃣ HEADER SECTION (replace previous header)
# -----------------------------------------------------------

col_left, col_right = st.columns([1, 11])

with col_left:
    st.write("")
    st.image("app/logo.png", width=90)

with col_right:
    st.markdown(
        """
        <div style="margin-bottom: 1.2rem;">
            <div class="app-title">Real Estate Visualization</div>
            <p class="app-subtitle">
                Explore listings by location, price, and bedrooms with an interactive dashboard.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")


# -----------------------------------------------------------
# 3️⃣ SIDEBAR WITH ICONS (update sidebar)
# -----------------------------------------------------------

render_sidebar_filters()

# Read current filter values from session_state
zip_code = st.session_state.get("zip_code", "")
state = st.session_state.get("state", "")
city = st.session_state.get("city", "")
min_price = st.session_state.get("min_price", 0)
max_price = st.session_state.get("max_price", 2_000_000)
min_beds = st.session_state.get("min_beds", 0)
max_beds = st.session_state.get("max_beds", 0)


# -----------------------------------------------------------
# 4️⃣ API LOGIC (unchanged from your original code)
# -----------------------------------------------------------

location_validity = {}
if zip_code:
    location_validity["zip_code"] = zip_code
elif city and state:
    location_validity["city"] = city
    location_validity["state"] = state

if location_validity:
    listings = fetch_listings(
        listing_type="sale",
        status=None,
        limit=1000,
        **location_validity,
    )

    if listings:
        save_listings_to_csv(
            listings, filename="data/listings_RentCastAPI.csv")
        st.write(f"Fetched {len(listings)} listings from RentCast.")
    else:
        st.warning(
            "No listings returned from RentCast with those location inputs.")
else:
    st.markdown(
        """
    <div style="
        background-color: rgba(255,255,255,0.05);
        padding: 0.75rem 1rem;
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.08);
        color: #cbd5e1;
        font-size: 0.9rem;
        margin-bottom: 1rem;">
        No search filters set — displaying existing CSV data.
    </div>
    """,
        unsafe_allow_html=True,
    )

df = load_first_csv("data")

# -----------------------------------------------------------
# 5️⃣ DATA DISPLAY + FILTERING (your logic, slightly polished)
# -----------------------------------------------------------

if df is None:
    st.info("No data yet. Add a CSV into the `data/` folder and reload.")
else:
    q = df.copy()
    q.columns = [str(c).strip().lower() for c in q.columns]

    # Detect important columns
    zip_columns = next(
        (c for c in ["zip", "zipcode", "postal_code"] if c in q.columns), None)
    price_columns = next(
        (c for c in ["price", "list_price", "listprice"] if c in q.columns), None)
    bed_columns = next(
        (c for c in ["beds", "bedrooms", "br"] if c in q.columns), None)

    # Apply filters
    if zip_code and zip_columns:
        q = q[q[zip_columns].astype(str).str.startswith(zip_code)]

    if price_columns:
        q = q[(q[price_columns] >= min_price) &
              (q[price_columns] <= max_price)]

    if bed_columns:
        q = q[q[bed_columns] >= min_beds]
        if max_beds > 0:
            q = q[q[bed_columns] <= max_beds]

    # Display section title
    st.markdown(
        "<div class='section-title'>📊 Match the Listings</div>",
        unsafe_allow_html=True,
    )

    # Small KPI row
    if not q.empty:
        k1, k2, k3 = st.columns(3)
        # total listings after filters
        k1.metric("Listings", f"{len(q):,}")

        # average price, if we found a price column
        if price_columns:
            avg_price = float(q[price_columns].mean())
            k2.metric("Avg price", f"${avg_price:,.0f}")
        else:
            k2.metric("Avg price", "N/A")

        # median beds, if we found a beds column
        if bed_columns:
            median_beds = float(q[bed_columns].median())
            k3.metric("Median beds", f"{median_beds:,.1f}")
        else:
            k3.metric("Median beds", "N/A")

    st.caption("Showing listings that match your filters.")
    st.dataframe(q, use_container_width=True, hide_index=True)
