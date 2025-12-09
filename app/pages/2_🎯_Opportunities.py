# app/pages/Opportunities.py
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
import pydeck as pdk

from utils.style import apply_theme
from utils.filters_ui import render_sidebar_filters
from rentCast_collectionV2 import fetch_listings, save_listings_to_csv

st.set_page_config(page_title="ROI", page_icon="⏳", layout="wide")
apply_theme()

# -----------------------------------------------------------
# 🔍 Shared sidebar + API trigger (same as Home/Map3D)
# -----------------------------------------------------------

# Draw the sidebar filters & buttons
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

# Decide what location to send to the API
location_validity = {}
if zip_code:
    location_validity["zip_code"] = zip_code
elif city and state:
    location_validity["city"] = city
    location_validity["state"] = state

# If the "Search listings" button was clicked on this page:
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


# ---------- load via your repo helper ----------


def _load_csv_from_repo() -> pd.DataFrame:
    try:
        from utils.io import load_first_csv
    except Exception:
        import sys
        sys.path.append(str(Path(__file__).resolve().parents[1]))
        from utils.io import load_first_csv
    try:
        return load_first_csv("data")
    except Exception as e:
        st.error(f"Could not load CSV from data/: {e}")
        return pd.DataFrame()

# ---------- helpers ----------


def _s(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col].astype(str).fillna("") if col in df.columns else pd.Series("", index=df.index)


@st.cache_data(show_spinner=False)
def prepare_df() -> pd.DataFrame:
    df = _load_csv_from_repo()
    if df.empty:
        return df

    # numeric cleaning
    for c in ("price", "bathrooms", "bedrooms", "daysOnMarket", "squareFootage", "yearBuilt", "lotSize", "hoa", "latitude", "longitude"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # strings
    for c in ("city", "state", "status", "propertyType", "zipCode"):
        if c in df:
            df[c] = df[c].astype(str).str.strip()
    # zip keep 5-digit where available
    if "zipCode" in df:
        raw = df["zipCode"].astype(str)
        five = raw.str.extract(r"(\d{5})", expand=False)
        df["zipCode"] = five.fillna(raw).str.strip()

    # $/sqft
    if {"price", "squareFootage"}.issubset(df.columns):
        df["pps"] = np.where(df["squareFootage"] > 0,
                             df["price"]/df["squareFootage"], np.nan)

    # friendly address
    if "formattedAddress" in df:
        df["addr"] = df["formattedAddress"].fillna("")
    else:
        df["addr"] = (_s(df, "addressLine1") + ", " + _s(df, "city") +
                      ", " + _s(df, "state") + " " + _s(df, "zipCode")).str.strip(", ")
    return df


df = prepare_df()
if df.empty or "price" not in df.columns:
    st.warning("No priced listings found in /data.")
    st.stop()

st.title("🎯 Opportunity Detector")

# ------------------ Filters ------------------
with st.expander("Filters", expanded=True):
    c1, c2, c3, c4, c5 = st.columns(5)
    states = sorted(df["state"].dropna().unique().tolist()
                    ) if "state" in df else []
    state_sel = c1.multiselect("State", states, default=states or None)
    d1 = df[df["state"].isin(state_sel)] if state_sel else df.copy()

    cities = sorted(d1["city"].dropna().unique().tolist()
                    ) if "city" in d1 else []
    city_sel = c2.multiselect("City", cities)
    d2 = d1[d1["city"].isin(city_sel)] if city_sel else d1

    zips = sorted(d2["zipCode"].dropna().unique().tolist()
                  ) if "zipCode" in d2 else []
    zip_sel = c3.multiselect("ZIP", zips)
    d3 = d2[d2["zipCode"].isin(zip_sel)] if zip_sel else d2

    statuses = sorted(d3["status"].dropna().unique().tolist()
                      ) if "status" in d3 else []
    status_sel = c4.multiselect("Status", statuses)
    d4 = d3[d3["status"].isin(status_sel)] if status_sel else d3

    types = sorted(d4["propertyType"].dropna().unique().tolist()
                   ) if "propertyType" in d4 else []
    type_sel = c5.multiselect("Property Type", types)
    filt = d4[d4["propertyType"].isin(type_sel)] if type_sel else d4

if filt.empty:
    st.warning("No listings after filters.")
    st.stop()

# ------------------ Controls ------------------
cA, cB, cC, cD = st.columns(4)
metric = cA.radio("Valuation metric", [
                  "Price", "Price per sqft"], horizontal=True)
group_choice = cB.radio("Comparables group", [
                        "ZIP", "Bedrooms", "ZIP+Bedrooms"], horizontal=True)
min_comps = int(cC.number_input("Min comps per group", 3, 50, 8))
top_n = int(cD.number_input("Top N undervalued", 5, 100, 15))

if metric == "Price per sqft":
    if "pps" not in filt:
        st.info("Price per sqft requires price and squareFootage.")
        st.stop()
    y = pd.to_numeric(filt["pps"], errors="coerce")
    metric_col = "pps"
else:
    y = pd.to_numeric(filt["price"], errors="coerce")
    metric_col = "price"

# group key
if group_choice == "ZIP+Bedrooms":
    need = {"zipCode", "bedrooms"}
    if not need.issubset(filt.columns):
        st.info("Need 'zipCode' and 'bedrooms' for ZIP+Bedrooms.")
        st.stop()
    filt["_grp"] = filt["zipCode"].astype(
        str) + " | " + filt["bedrooms"].astype("Int64").astype(str)
elif group_choice == "ZIP":
    if "zipCode" not in filt:
        st.info("Need zipCode")
        st.stop()
    filt["_grp"] = filt["zipCode"].astype(str)
else:
    if "bedrooms" not in filt:
        st.info("Need bedrooms")
        st.stop()
    filt["_grp"] = filt["bedrooms"].astype("Int64").astype(str)

# keep only groups with enough comps
sizes = filt.groupby("_grp")[metric_col].transform("count")
work = filt[sizes >= min_comps].copy()
if work.empty:
    st.warning("No groups meet the minimum comps requirement.")
    st.stop()

# robust center / dispersion (median & MAD) per group
med = work.groupby("_grp")[metric_col].transform("median")
mad = (work[metric_col] - med).abs().groupby(work["_grp"]).transform("median")
scale = (1.4826 * mad).replace(0, np.nan)  # Normal-equivalent MAD

# empirical percentile (non-parametric)


def _percentile_rank(x, g, series):
    grp = series[g == x["_grp"]]
    return (grp.rank(pct=True, method="average")[x.name])


prct = work.apply(lambda r: _percentile_rank(
    r, work["_grp"], work[metric_col]), axis=1)

work["group_median"] = med
work["robust_z"] = (work[metric_col] - med) / scale
work["percentile"] = prct  # 0..1 within group
work["discount_%"] = (1.0 - (work[metric_col] / med)) * 100.0

# probability the listing is below group median = empirical percentile
work["p_below_median_%"] = (work["percentile"] * 100.0).round(1)

# rank by strongest undervaluation signal: lower z, higher discount, lower percentile
ranked = work.sort_values(
    by=["robust_z", "discount_%", "percentile"], ascending=[True, False, True]
).head(top_n)

st.markdown("### Top candidates (by robust z, discount % and percentile)")
show_cols = [c for c in ["addr", "zipCode", "bedrooms", "price", "pps", "group_median",
                         "discount_%", "robust_z", "p_below_median_%", "daysOnMarket", "status"] if c in ranked.columns]
st.dataframe(
    ranked[show_cols].style.format({"price": ",.0f", "pps": ",.0f", "group_median": ",.0f",
                                    "discount_%": "{:.1f}", "robust_z": "{:.2f}", "p_below_median_%": "{:.1f}"}),
    use_container_width=True, hide_index=True
)

# optional tiny map of top picks
if {"latitude", "longitude"}.issubset(ranked.columns):
    with st.expander("Map the candidates", expanded=False):
        m = ranked.dropna(subset=["latitude", "longitude"]).copy()
        if not m.empty:
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=m, get_position="[longitude, latitude]",
                get_radius=70, pickable=True,
                get_fill_color=[59, 130, 246, 180]
            )
            view = pdk.ViewState(
                longitude=float(m["longitude"].mean()),
                latitude=float(m["latitude"].mean()),
                zoom=10, pitch=40
            )
            st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, map_provider="carto", map_style="light"),
                            use_container_width=True, height=420)

# distribution peek for any selected group
grp_to_inspect = st.selectbox(
    "Inspect distribution for group", sorted(work["_grp"].unique()))
gdf = work.loc[work["_grp"] == grp_to_inspect, [metric_col]]
hist = alt.Chart(gdf).transform_bin("bin", field=metric_col).mark_bar().encode(
    x=alt.X("bin:Q", title=f"{metric}"),
    y=alt.Y("count()", title="# Listings"),
    tooltip=[alt.Tooltip("count()", title="# Listings")]
).properties(height=240)
st.altair_chart(hist, use_container_width=True)
st.caption(
    "Probabilities are empirical: each listing’s percentile within its comps group.")
