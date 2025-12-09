import os
import shutil
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
# 2️⃣ HEADER
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
# 🌍 Load full dataset from rent_listings.csv
# -----------------------------------------------------------
if st.button("🌍 Load full dataset", help="Restore the full dataset from rent_listings.csv"):
    base_path = "data/rent_listings.csv"
    target_path = "data/listings_RentCastAPI.csv"

    if os.path.exists(base_path):
        shutil.copyfile(base_path, target_path)
        st.success("Full dataset loaded from rent_listings.csv. All pages now use this data.")
        try:
            st.rerun()
        except Exception:
            st.experimental_rerun()
    else:
        st.error("data/rent_listings.csv not found. Please add it to the data/ folder.")


# -----------------------------------------------------------
# 3️⃣ SIDEBAR FILTERS
# -----------------------------------------------------------

search_clicked = render_sidebar_filters()

# Read current filter values from session_state
zip_code = st.session_state.get("zip_code", "")
state = st.session_state.get("state", "")
city = st.session_state.get("city", "")
min_price = st.session_state.get("min_price", 0)
max_price = st.session_state.get("max_price", 2_000_000)
min_beds = st.session_state.get("min_beds", 0)
max_beds = st.session_state.get("max_beds", 0)

property_type_options = st.session_state.get("property_type_options", [])
status_option = st.session_state.get("status_option", "Any")
min_year = st.session_state.get("min_year", 0)
max_year = st.session_state.get("max_year", 0)
min_sqft = st.session_state.get("min_sqft", 0)
max_sqft = st.session_state.get("max_sqft", 0)
min_ppsqft = st.session_state.get("min_ppsqft", 0)
max_ppsqft = st.session_state.get("max_ppsqft", 0)


# -----------------------------------------------------------
# 4️⃣ API LOGIC (Search button)
# -----------------------------------------------------------

location_validity = {}
if zip_code:
    # prefer ZIP if entered
    location_validity["zip_code"] = zip_code
elif city and state:
    location_validity["city"] = city
    location_validity["state"] = state

if search_clicked:
    # Only hit API when user explicitly clicks the button
    if not location_validity:
        st.warning(
            "Please enter either a ZIP code or both City and State before searching."
        )
    else:
        filter_kwargs = {}

        # Property type: send first selected type (API expects one)
        if property_type_options:
            filter_kwargs["property_type"] = property_type_options[0]

        # Status: None means "Any" for the API
        api_status = None if status_option == "Any" else status_option

        # Numeric ranges: treat 0 as "no limit"
        filter_kwargs["min_price"] = min_price or None
        filter_kwargs["max_price"] = max_price or None
        filter_kwargs["min_bedrooms"] = min_beds or None
        filter_kwargs["max_bedrooms"] = max_beds or None
        filter_kwargs["min_year"] = min_year or None
        filter_kwargs["max_year"] = max_year or None
        filter_kwargs["min_sqft"] = min_sqft or None
        filter_kwargs["max_sqft"] = max_sqft or None

        with st.spinner("Fetching listings from RentCast..."):
            listings = fetch_listings(
                listing_type="sale",
                status=api_status,
                limit=1000,
                **location_validity,
                **filter_kwargs,
            )

        if listings:
            save_listings_to_csv(
                listings, filename="data/listings_RentCastAPI.csv"
            )
            st.success(f"Fetched {len(listings)} listings from RentCast.")
        else:
            st.warning("No listings returned from RentCast with those filters.")
else:
    # No search click yet
    if not location_validity:
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
    else:
        st.info("Location set. Click 'Search listings' to fetch fresh data.")


# -----------------------------------------------------------
# 5️⃣ LOAD DATA
# -----------------------------------------------------------

df = load_first_csv("data")

if df is None:
    st.info("No data yet. Add a CSV into the `data/` folder and reload.")
else:
    q = df.copy()
    q.columns = [str(c).strip().lower() for c in q.columns]

    # -------------------------------------------------------
    # 6️⃣ COLUMN DETECTION
    # -------------------------------------------------------

    zip_columns = next(
        (c for c in ["zip", "zipcode", "postal_code"] if c in q.columns), None
    )
    price_columns = next(
        (c for c in ["price", "list_price", "listprice"] if c in q.columns), None
    )
    bed_columns = next(
        (c for c in ["beds", "bedrooms", "br"] if c in q.columns), None
    )

    property_type_col = next(
        (c for c in ["propertytype", "property_type", "type"] if c in q.columns), None
    )
    status_col = "status" if "status" in q.columns else None
    year_col = next(
        (c for c in ["yearbuilt", "year_built"] if c in q.columns), None
    )
    sqft_col = next(
        (c for c in ["squarefootage", "sqft", "livingarea"] if c in q.columns), None
    )

    # compute price per sqft if possible
    ppsqft_col = None
    if price_columns and sqft_col:
        ppsqft_col = "price_per_sqft"
        q[ppsqft_col] = q[price_columns] / q[sqft_col].replace({0: None})

    # -------------------------------------------------------
    # 7️⃣ APPLY FILTERS (0 / empty = "no filter")
    # -------------------------------------------------------

    # ZIP (string prefix match)
    if zip_code and zip_columns:
        q = q[q[zip_columns].astype(str).str.startswith(str(zip_code))]

    # price range (0 means "no limit")
    if price_columns:
        if min_price > 0:
            q = q[q[price_columns] >= min_price]
        if max_price > 0:
            q = q[q[price_columns] <= max_price]

    # beds range
    if bed_columns:
        if min_beds > 0:
            q = q[q[bed_columns] >= min_beds]
        if max_beds > 0:
            q = q[q[bed_columns] <= max_beds]

    # property type (multi-select)
    if property_type_col and property_type_options:
        q = q[q[property_type_col].isin(property_type_options)]

    # status ("Any" means no filter)
    if status_col and status_option != "Any":
        q = q[
            q[status_col].astype(str).str.lower()
            == status_option.lower()
        ]

    # year built range
    if year_col:
        if min_year > 0:
            q = q[q[year_col] >= min_year]
        if max_year > 0:
            q = q[q[year_col] <= max_year]

    # square footage range
    if sqft_col:
        if min_sqft > 0:
            q = q[q[sqft_col] >= min_sqft]
        if max_sqft > 0:
            q = q[q[sqft_col] <= max_sqft]

    # price per sqft range (only if we have that column)
    if ppsqft_col:
        if min_ppsqft > 0:
            q = q[q[ppsqft_col] >= min_ppsqft]
        if max_ppsqft > 0:
            q = q[q[ppsqft_col] <= max_ppsqft]

    # -------------------------------------------------------
    # 8️⃣ UI: TITLE, KPIs, TABLE
    # -------------------------------------------------------

    st.markdown(
        "<div class='section-title'>📊 Match the Listings</div>",
        unsafe_allow_html=True,
    )

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
