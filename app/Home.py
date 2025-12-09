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

import streamlit.components.v1 as components

# get image
import base64
def get_base64_image(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("utf-8")
hero_img = get_base64_image("app/hero-header.png")


# header
components.html(
    f"""
    <style>
        .hero-container {{
            position: relative;
            width: 100%;
            height: 320px;  /* taller so search fits */
            background-image: url('data:image/png;base64,{hero_img}');
            background-size: cover;
            background-position: center 25%;
            border-radius: 12px;
            overflow: hidden;  /* don't clip the search bar */
        }}


        .hero-overlay {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(
                to bottom,
                rgba(0, 0, 0, 0.55),
                rgba(0, 0, 0, 0.25)
            );
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }}

        .hero-title {{
            font-size: 2.7rem;
            font-weight: 700;
            color: white;
            margin-bottom: 0.4rem;
        }}

        .hero-subtitle {{
            font-size: 1.15rem;
            color: #e5e7eb;
            max-width: 600px;
            margin-bottom: 1.8rem;
        }}

        .hero-search-wrapper {{
            position: absolute;
            bottom: 20px;
            width: 100%;
            display: flex;
            justify-content: center;
        }}

        .hero-search {{
            background: white;
            padding: 0.75rem 1rem;
            border-radius: 999px;
            display: flex;
            gap: 0.5rem;
            box-shadow: 0 8px 20px rgba(0,0,0,0.25);
        }}

        .hero-search input {{
            padding: 0.55rem 1rem;
            min-width: 260px;
            border-radius: 999px;
            border: none;
            outline: none;
            font-size: 0.95rem;
        }}

        .hero-search button {{
            padding: 0.55rem 1.2rem;
            border-radius: 999px;
            border: none;
            background: linear-gradient(135deg, #e63946, #b81f2d);
            color: white;
            font-weight: 600;
            cursor: pointer;
        }}
    </style>

    <div class="hero-container">

        <div class="hero-overlay">
            <h1 class="hero-title">Real Estate Visualization</h1>
            <p class="hero-subtitle">
                Explore listings, analyze neighborhoods, and understand market trends—all in one place.
            </p>
        </div>

        <div class="hero-search-wrapper">
            <div class="hero-search">
                <input type="text" placeholder="Search by city, zip code, or neighborhood">
                <button>Search</button>
            </div>
        </div>

    </div>
    """,
    height=350
)

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



# -----------------------------------------------------------
# 5️⃣ LOAD DATA
# -----------------------------------------------------------

df = load_first_csv("data")

if df is None:
    st.info("No data yet. Add a CSV into the `data/` folder and reload.")

else:
    # ---------- Prep mini-map data (m) ----------
    m = df.copy()
    for c in ("latitude", "longitude", "price"):
        if c in m.columns:
            m[c] = pd.to_numeric(m[c], errors="coerce")

    if {"latitude", "longitude"}.issubset(m.columns):
        m = m.dropna(subset=["latitude", "longitude"])
        m = m[(m["latitude"].between(-90, 90)) & (m["longitude"].between(-180, 180))]
        m = m.head(500)  # cap for speed
    else:
        m = m.iloc[0:0]

    # ---------- 3D MAP HOME SECTION ----------

    st.markdown(
        "<div class='big-section-title'>Explore your market in 3D</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1.4, 2])

    with col1:
        st.markdown(
            """
            ### 🗺️ 3D Neighborhood Map

            Understand <em>where</em> listings are, not just their prices.

            - See clusters and hot spots  
            - Compare neighborhoods at a glance  
            - View price patterns by location  
            """,
            unsafe_allow_html=True,
        )

        try:
            if st.button("Open 3D Map", use_container_width=True, key="open_map3d"):
                st.switch_page("pages/Map3D.py")
        except Exception:
            st.caption("Use the sidebar to open the **3D Map** page.")

    with col2:
        if m.empty:
            st.caption("No listings with coordinates available yet to preview the map.")
        else:
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=m,
                get_position="[longitude, latitude]",
                get_radius=60,
                get_fill_color=[59, 130, 246, 180],
                pickable=False,
            )
            view_state = pdk.ViewState(
                longitude=float(m["longitude"].mean()),
                latitude=float(m["latitude"].mean()),
                zoom=9,
                pitch=45,
            )
            deck = pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                map_provider="carto",
                map_style="dark",
            )
            st.pydeck_chart(deck, use_container_width=True, height=260)



    # -------------------------------------------------------
    # 6️⃣ COLUMN DETECTION (for filters)
    # -------------------------------------------------------
    q = df.copy()
    q.columns = [str(c).strip().lower() for c in q.columns]

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
        (c for c in ["propertytype", "property_type", "type"] if c in q.columns),
        None,
    )
    status_col = "status" if "status" in q.columns else None
    year_col = next(
        (c for c in ["yearbuilt", "year_built"] if c in q.columns),
        None,
    )
    sqft_col = next(
        (c for c in ["squarefootage", "sqft", "livingarea"] if c in q.columns),
        None,
    )

    # compute price per sqft if possible
    ppsqft_col = None
    if price_columns and sqft_col:
        ppsqft_col = "price_per_sqft"
        q[ppsqft_col] = q[price_columns] / q[sqft_col].replace({0: None})

    # -------------------------------------------------------
    # 7️⃣ APPLY FILTERS (0 / empty = "no filter")
    # -------------------------------------------------------
    if zip_code and zip_columns:
        q = q[q[zip_columns].astype(str).str.startswith(str(zip_code))]

    if price_columns:
        if min_price > 0:
            q = q[q[price_columns] >= min_price]
        if max_price > 0:
            q = q[q[price_columns] <= max_price]

    if bed_columns:
        if min_beds > 0:
            q = q[q[bed_columns] >= min_beds]
        if max_beds > 0:
            q = q[q[bed_columns] <= max_beds]

    if property_type_col and property_type_options:
        q = q[q[property_type_col].isin(property_type_options)]

    if status_col and status_option != "Any":
        q = q[
            q[status_col].astype(str).str.lower()
            == status_option.lower()
        ]

    if year_col:
        if min_year > 0:
            q = q[q[year_col] >= min_year]
        if max_year > 0:
            q = q[q[year_col] <= max_year]

    if sqft_col:
        if min_sqft > 0:
            q = q[q[sqft_col] >= min_sqft]
        if max_sqft > 0:
            q = q[q[sqft_col] <= max_sqft]

    if ppsqft_col:
        if min_ppsqft > 0:
            q = q[q[ppsqft_col] >= min_ppsqft]
        if max_ppsqft > 0:
            q = q[q[ppsqft_col] <= max_ppsqft]

    # -------------------------------------------------------
    # 8️⃣ RAW DATA TABLE (inside a darker section block)
    # -------------------------------------------------------

    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)

    st.markdown(
        "<div class='big-section-title'>The live raw data we are processing.</div>",
        unsafe_allow_html=True,
    )

    st.caption(
        "We take this data and transform it into maps, graphs, and trends to help you decide on your next home!"
    )
    st.dataframe(df, use_container_width=True, hide_index=True)



    # -------------------------------------------------------
    # 9️⃣ GET IN CONTACT W/ AGENT
    # -------------------------------------------------------

    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    
    st.markdown(
        "<div class='contact-section'><div class='big-section-title'>Get in contact with a Real Estate Agent!</div>",
        unsafe_allow_html=True,
    )


    c1, c2 = st.columns([1.2, 1.5])

    with c1:
        st.markdown(
            """
            If you would like to inquire about any of the listings, enter your information to get connected to a real estate agent to learn more.

            (This form is for demonstration only and does not send real messages.)
            """,
        )
        center = st.columns([1, 4, 1])

        with center[1]:
            st.image("app/agent.png", width=250)

    with c2:
        name = st.text_input("Your name", key="agent_name")
        email = st.text_input("Email", key="agent_email")
        goal = st.selectbox(
            "What are you looking for?",
            ["Just exploring", "Buying a home", "Investment property", "Comparing markets"],
            key="agent_goal",
        )
        message = st.text_area(
            "Optional message",
            key="agent_message",
            height=80,
            placeholder="Tell us what kind of property or area you're interested in...",
        )

        st.button("Submit inquiry (demo)", key="agent_submit")

    st.markdown("</div>", unsafe_allow_html=True)


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
