# app/pages/Opportunities.py
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
import pydeck as pdk

from utils.style import apply_theme

st.set_page_config(page_title="ROI", page_icon="⏳", layout="wide")
apply_theme()



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
