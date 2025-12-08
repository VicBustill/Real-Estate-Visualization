import os
import time  # For build transition
import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import pydeck as pdk  # type: ignore
from utils.io import load_first_csv
from rentCast_collectionV2 import fetch_listings, save_listings_to_csv


# --- Styling ---
st.markdown(
    """<style> 
           /* Main background*/
           .stApp {
               background-color: #000000;
               color: white;
           }
           </style>""",
    unsafe_allow_html=True,
)

st.set_page_config(page_title="Real Estate Dashboard", layout="wide")

# --- Header layout ---
col_left, col_right = st.columns([1, 11])

with col_left:
    st.write("")
    st.image("app/logo.png", width=100, caption="")
with col_right:
    st.markdown(
        """<h1 style = 'color: white; margin-bottom: 0px;'> Real Estate Visualization</h1>""",
        unsafe_allow_html=True,
    )

st.caption(
    "Drop your real data CSVs into the `data/` folder. This app reads the first CSV it finds."
)

# Initial debug load
df = load_first_csv("data")  # This should be later
st.write("DEBUG: DataFrame result ->", df)
st.write("DEBUG: Loaded CSVs ->", os.listdir("data"))
st.write("DEBUG: DataFrame type ->", type(df))


# --- Sidebar filters ---
with st.sidebar:
    st.header("Filters")
    # One of the parameters for our API 1/3
    zip_code = st.text_input("ZIP (optional)", "")
    # One of the parameters for our API 2/3
    state = st.text_input("Abbreviated State", "")
    city = st.text_input("City", "")  # One of the parameters for our API 3/3

    min_price = st.number_input("Min price", min_value=0, value=0, step=50000)
    max_price = st.number_input(
        "Max price", min_value=0, value=2_000_000, step=50000
    )
    min_beds = st.number_input("Min beds", min_value=0, value=0, step=1)
    max_beds = st.number_input("Max beds", min_value=0, value=0, step=1)

    # New Filters
    property_type_options = st.multiselect(
        "Property type",
        options=["Single Family", "Condo",
                 "Townhouse", "Multi-Family", "Apartment"],
        default=[],
    )

    status_option = st.selectbox(
        "Status",
        options=["Any", "Active", "Inactive", "Sold"],
        index=0,
    )

    min_year = st.number_input("Min year built", min_value=0, value=0, step=5)
    max_year = st.number_input("Max year built", min_value=0, value=0, step=5)

    min_sqft = st.number_input(
        "Min square footage", min_value=0, value=0, step=100
    )
    max_sqft = st.number_input(
        "Max square footage", min_value=0, value=0, step=100
    )

    min_ppsqft = st.number_input(
        "Min price per sq ft", min_value=0, value=0, step=50
    )
    max_ppsqft = st.number_input(
        "Max price per sq ft", min_value=0, value=0, step=50
    )

    # 🔍 NEW: explicit search trigger for the API (For Builds)
    search_clicked = st.button("Search listings")


# ______________This section will make the API call ______________________________

# This should help with location searches and validation (IMPORTANT)
location_validity = {}
if zip_code:
    # Prefer ZIP if the user typed one
    location_validity["zip_code"] = zip_code
elif city and state:
    # Otherwise require BOTH city and state
    location_validity["city"] = city
    location_validity["state"] = state

# Only call the API when the Search button is clicked
if search_clicked:
    if not location_validity:
        st.warning(
            "Please enter either a ZIP code or both City and State before searching."
        )
    else:
        # --- build extra filters for the API ---
        filter_kwargs = {}

        # Property type: for now, just use the first selected option if any
        if property_type_options:
            filter_kwargs["property_type"] = property_type_options[0]

        # Status: send None if the user chose "Any"
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

        # 🔍 DEBUG: show exactly what we’re sending to the API
        st.write("DEBUG: location_validity ->", location_validity)
        st.write("DEBUG: filter_kwargs ->", filter_kwargs)
        st.write("DEBUG: api_status ->", api_status)

        # Optional spinner so the user sees a loading state
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

            # Tiny delay so the transition feels smoother (Im using this to help me build the data)
            time.sleep(0.5)

            st.success(f"Fetched {len(listings)} listings from RentCast.")
        else:
            st.warning("No listings returned from RentCast with those filters.")
            st.warning("Listing does not exist")
else:
    # No search click yet
    if not location_validity:
        st.info("Using existing CSV data in `data/` (no API location input yet).")
    else:
        # User has entered a location but hasn't clicked search
        st.info("Location set. Click 'Search listings' to fetch fresh data.")


# _______________________New data if API is called_________________________________

df = load_first_csv("data")


# __________________________________________________________________________

# fixing the CSV data
if df is None:
    st.info("No data yet. Add a CSV into the `data/` folder and reload.")
else:
    q = df.copy()

    # normalize column names (lowercase, no extra spaces)
    q.columns = [str(c).strip().lower() for c in q.columns]

    # --- detect important columns ---

    zip_col = None
    for name in ["zip", "zipcode", "postal_code", "zipcode"]:
        if name in q.columns:
            zip_col = name
            break

    price_col = None
    for name in ["price", "list_price", "listprice"]:
        if name in q.columns:
            price_col = name
            break

    beds_col = None
    for name in ["beds", "bedrooms", "br"]:
        if name in q.columns:
            beds_col = name
            break

    property_type_col = None
    for name in ["propertytype", "property_type", "type"]:
        if name in q.columns:
            property_type_col = name
            break

    status_col = None
    for name in ["status"]:
        if name in q.columns:
            status_col = name
            break

    year_col = None
    for name in ["yearbuilt", "year_built"]:
        if name in q.columns:
            year_col = name
            break

    sqft_col = None
    for name in ["squarefootage", "sqft", "livingarea"]:
        if name in q.columns:
            sqft_col = name
            break

    # compute price per sqft if we can
    ppsqft_col = None
    if price_col and sqft_col:
        ppsqft_col = "price_per_sqft"
        # avoid division by zero
        q[ppsqft_col] = q[price_col] / q[sqft_col].replace({0: None})

    # --- apply filters from sidebar ---

    # ZIP (string prefix match)
    if zip_code and zip_col:
        q = q[q[zip_col].astype(str).str.startswith(zip_code)]

    # price range (0 means "no limit")
    if price_col:
        if min_price > 0:
            q = q[q[price_col] >= min_price]
        if max_price > 0:
            q = q[q[price_col] <= max_price]

    # beds range
    if beds_col:
        if min_beds > 0:
            q = q[q[beds_col] >= min_beds]
        if max_beds > 0:
            q = q[q[beds_col] <= max_beds]

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

    st.subheader("Match the Listings")
    st.dataframe(q)

    # not sure if yall are up for it but maybe we can implement a chart displaying these listings or whatnot
