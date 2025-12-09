# app/pages/Map3D.py
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
import pydeck as pdk
from pathlib import Path
import os
import shutil

from utils.style import apply_theme
from utils.filters_ui import render_sidebar_filters
from rentCast_collectionV2 import fetch_listings, save_listings_to_csv

st.set_page_config(page_title="Map3D", page_icon="🗺️", layout="wide")
apply_theme()

# -----------------------------------------------------------
# 🔁 Handle map reset (must happen BEFORE sidebar widgets)
# -----------------------------------------------------------
if st.session_state.get("reset_map_flag", False):
    # Clear sidebar filters (same defaults as Reset Filters button)
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

    # clear the flag so it doesn't keep resetting
    st.session_state["reset_map_flag"] = False


# Sidebar filters + buttons (shared with Home)
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
# 🔍 API trigger on Map3D too
# -----------------------------------------------------------
location_validity = {}
if zip_code:
    location_validity["zip_code"] = zip_code
elif city and state:
    location_validity["city"] = city
    location_validity["state"] = state

if search_clicked:
    if not location_validity:
        st.warning(
            "Please enter either a ZIP code or both City and State before searching."
        )
    else:
        filter_kwargs = {}

        # Property type: use first selected option if any
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


# ---- use your repo's loader (works from any page) ----


def _load_csv_from_repo() -> pd.DataFrame:
    try:
        from utils.io import load_first_csv  # normal path when running app/app.py
    except Exception:
        # add app/ to sys.path if pages run in a different context
        import sys
        sys.path.append(str(Path(__file__).resolve().parents[1]))
        from utils.io import load_first_csv
    try:
        return load_first_csv("data")
    except Exception as e:
        st.error(f"Could not load CSV from data/: {e}")
        return pd.DataFrame()


df = _load_csv_from_repo()
if df.empty:
    st.warning(
        "No data found under /data. Ensure your CSV is in the data/ folder.")
    st.stop()

# ---- minimal cleaning for the map ----
for c in ("price", "latitude", "longitude", "bedrooms", "bathrooms", "squareFootage", "yearBuilt", "daysOnMarket"):
    if c in df:
        df[c] = pd.to_numeric(df[c], errors="coerce")
if "addr" not in df:
    a1 = df.get("addressLine1", pd.Series(
        "", index=df.index)).astype(str).fillna("")
    c = df.get("city",         pd.Series(
        "", index=df.index)).astype(str).fillna("")
    s = df.get("state",        pd.Series(
        "", index=df.index)).astype(str).fillna("")
    z = df.get("zipCode",      pd.Series(
        "", index=df.index)).astype(str).fillna("")
    df["addr"] = (a1 + ", " + c + ", " + s + " " + z).str.strip(", ")


m = df.dropna(subset=["latitude", "longitude"]).copy()
m = m[(m["latitude"].between(-90, 90)) & (m["longitude"].between(-180, 180))]
m = m[(m["latitude"] != 0) & (m["longitude"] != 0)]

# -----------------------------------------------------------
# 🔍 Apply the same sidebar filters as Home, but to map data
# -----------------------------------------------------------

# Detect important columns in the original casing
zip_col = None
for name in ["zipCode", "zipcode", "postal_code", "zip"]:
    if name in m.columns:
        zip_col = name
        break

price_col = None
for name in ["price", "list_price", "listPrice"]:
    if name in m.columns:
        price_col = name
        break

beds_col = None
for name in ["bedrooms", "beds", "br"]:
    if name in m.columns:
        beds_col = name
        break

property_type_col = None
for name in ["propertyType", "property_type", "type"]:
    if name in m.columns:
        property_type_col = name
        break

status_col = "status" if "status" in m.columns else None

year_col = None
for name in ["yearBuilt", "year_built"]:
    if name in m.columns:
        year_col = name
        break

sqft_col = None
for name in ["squareFootage", "sqft", "livingArea"]:
    if name in m.columns:
        sqft_col = name
        break

# ZIP (string prefix)
if zip_code and zip_col:
    m = m[m[zip_col].astype(str).str.startswith(str(zip_code))]

# price range
if price_col:
    if min_price > 0:
        m = m[m[price_col] >= min_price]
    if max_price > 0:
        m = m[m[price_col] <= max_price]

# beds range
if beds_col:
    if min_beds > 0:
        m = m[m[beds_col] >= min_beds]
    if max_beds > 0:
        m = m[m[beds_col] <= max_beds]

# property type
if property_type_col and property_type_options:
    m = m[m[property_type_col].isin(property_type_options)]

# status
if status_col and status_option != "Any":
    m = m[
        m[status_col].astype(str).str.lower()
        == status_option.lower()
    ]

# year built
if year_col:
    if min_year > 0:
        m = m[m[year_col] >= min_year]
    if max_year > 0:
        m = m[m[year_col] <= max_year]

# square footage
if sqft_col:
    if min_sqft > 0:
        m = m[m[sqft_col] >= min_sqft]
    if max_sqft > 0:
        m = m[m[sqft_col] <= max_sqft]





st.title("🗺️ 3D Map")
st.caption("Add filters for searching across the map on the sidebar filtered search. Press 'Search listings' to show desired filters.")


# 🔄 Reset map: restore full dataset + clear filters
if st.button("🔄 Reset map", help="Clear filters and restore full dataset", key="reset_map"):
    # 1) Restore the original full dataset
    base_path = "data/rent_listings.csv"          # original full data
    target_path = "data/listings_RentCastAPI.csv" # working data file used by pages

    if os.path.exists(base_path):
        shutil.copyfile(base_path, target_path)
        st.success("Reset complete: full dataset restored.")
    else:
        st.warning("Could not find data/rent_listings.csv to restore from.")

    # 2) Tell the *next* run to clear filters before rendering sidebar
    st.session_state["reset_map_flag"] = True

    # 3) Rerun the app so the reset takes effect
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


st.caption("Press button above to reset map to show all listings.")
if m.empty:
    st.info("No valid coordinates to plot.")
    st.stop()


# color/size by price
p = pd.to_numeric(m.get("price"), errors="coerce")
if p.notna().any():
    p_min, p_max = float(np.nanmin(p)), float(np.nanmax(p))
    norm = (p - p_min) / \
        (p_max - p_min) if p_max > p_min else pd.Series(0.5, index=m.index)
else:
    p_min = p_max = 0.0
    norm = pd.Series(0.5, index=m.index)

m["price_norm"] = norm.fillna(0.5)
m["price_label"] = p.map(lambda v: f"${v:,.0f}" if pd.notna(v) else "N/A")
m["col_r"] = (norm * 255).round().astype(int)
m["col_g"] = 64
m["col_b"] = (255 - norm * 255).round().astype(int)
m["radius_m"] = ((norm * 120) + 40).astype(float)
m.attrs["p_min"] = p_min
m.attrs["p_med"] = float(np.nanmedian(p)) if p.notna().any() else 0.0
m.attrs["p_max"] = p_max

left, right = st.columns(2)
use_pins = left.toggle("Show pin icons", value=True)
use_columns = right.toggle("Show 3D columns by price", value=False)

layers = []
if use_pins:
    m["icon"] = [{
        "url": "https://raw.githubusercontent.com/visgl/deck.gl-data/master/icon/marker.png",
        "width": 128, "height": 128, "anchorY": 128,
    }] * len(m)
    layers.append(pdk.Layer(
        "IconLayer", data=m, get_icon="icon", get_size=4, size_scale=8,
        get_position="[longitude, latitude]", pickable=True
    ))

if use_columns:
    m["elev"] = (m["price_norm"] * 1200 + 200).astype(float)
    layers.append(pdk.Layer(
        "ColumnLayer", data=m, get_position="[longitude, latitude]", get_elevation="elev",
        elevation_scale=1, radius=40, extruded=True, pickable=True, get_fill_color="[col_r, col_g, col_b]"
    ))

layers.append(pdk.Layer(
    "ScatterplotLayer", data=m, get_position="[longitude, latitude]",
    get_radius="radius_m", pickable=True, get_fill_color="[col_r, col_g, col_b]", opacity=0.35
))

view_state = pdk.ViewState(
    longitude=float(m["longitude"].mean()),
    latitude=float(m["latitude"].mean()),
    zoom=10, pitch=60, bearing=-15,
)

tooltip = {
    "html": (
        "<b>{addr}</b><br/><b>{price_label}</b>"
        + (" • {bedrooms} bd" if "bedrooms" in m else "")
        + (" / {bathrooms} ba" if "bathrooms" in m else "")
        + ("<br/>{squareFootage} sqft" if "squareFootage" in m else "")
        + (" • Built {yearBuilt}" if "yearBuilt" in m else "")
        + ("<br/>DOM: {daysOnMarket}" if "daysOnMarket" in m else "")
        + (" • {status}" if "status" in m else "")
    ),
    "style": {"backgroundColor": "#1f2937", "color": "white"},
}
# --- SAFE Mapbox token handling ---
# ---- Build the Deck (works with or without Mapbox token) ----

# Try Mapbox first if you have a token; otherwise fall back to Carto (no token required)
token = os.getenv("MAPBOX_API_KEY")
if not token:
    try:
        token = st.secrets["MAPBOX_API_KEY"]  # may not exist; that's fine
    except Exception:
        token = None

if token:
    pdk.settings.mapbox_api_key = token
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v11",
        tooltip=tooltip,
    )
else:
    # Carto provider does not need any key
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_provider="carto",   # <- important: use Carto tiles
        map_style="light",      # 'light' or 'dark'
        tooltip=tooltip,
    )

# Ensure there is at least one visible layer
if not layers:
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        data=m,
        get_position="[longitude, latitude]",
        get_radius=60,
        get_fill_color=[59, 130, 246],
        pickable=False,
    ))
    deck.layers = layers

# Render with an explicit height so it’s visible
st.pydeck_chart(deck, use_container_width=True, height=600)


# -------------------------------------------------------
# 🔚 Simple Streamlit Footer 
# -------------------------------------------------------

with st.container():
    st.markdown("---")

    col_left, col_right = st.columns([1, 4])

    # Left side: copyright / name
    with col_left:
        st.caption("© 2025 Real Estate Visualization")

    # Right side: simple page links
    with col_right:
        link_cols = st.columns(6)

        with link_cols[0]:
            st.page_link("Home.py", label="Home", icon="🏠")

        with link_cols[1]:
            st.page_link("pages/1_🗺️_Map3D.py", label="3D Map", icon="🗺️")

        with link_cols[2]:
            st.page_link("pages/2_🎯_Opportunities.py", label="Opportunities", icon="🎯")
        
        with link_cols[3]:
            st.page_link("pages/3_⏳_ROI.py", label="ROI", icon="⏳")

        with link_cols[4]:
            st.page_link("pages/4_🧭_Stability.py", label="Stability", icon="🧭")

        with link_cols[5]:
            st.page_link("pages/5_📈_Trends.py", label="Trends", icon="📈")
