# app/trends.py

import altair as alt
import pydeck as pdk
import pandas as pd
import numpy as np
import streamlit as st


def _first_match(cols, candidates):
    lower = {c.lower(): c for c in cols}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    variants = {
        "price": ["price", "list_price", "sale_price", "amount"],
        "zip": ["zip", "zipcode", "postal_code", "zip_code"],
        "bedrooms": ["bedrooms", "beds", "br", "num_bedrooms"],
        "latitude": ["latitude", "lat", "y"],
        "longitude": ["longitude", "lon", "lng", "x"],
        "address": ["address", "street_address", "full_address", "addr", "street"],
    }
    df = df.copy()
    mapping = {}
    cols = list(df.columns)
    for canon, cands in variants.items():
        m = _first_match(cols, cands)
        if m:
            mapping[m] = canon
    if mapping:
        df = df.rename(columns=mapping)
    if "zip" in df:
        df["zip"] = df["zip"].astype(str)
    if "bedrooms" in df:
        df["bedrooms"] = pd.to_numeric(
            df["bedrooms"], errors="coerce").astype("Int64")
    if "price" in df:
        df["price"] = pd.to_numeric(
            df["price"], errors="coerce").astype("float32")
    for c in ("latitude", "longitude"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float32")
    return df


def render_trends(df: pd.DataFrame) -> None:
    df_norm = normalize_columns(df).dropna(subset=["price"])

    st.header("📈 Trends")

    group_by = st.radio("Average price by", [
                        "ZIP", "Bedrooms"], horizontal=True)
    by_col, x_title = None, ""
    if group_by == "ZIP" and "zip" in df_norm:
        by_col, x_title = "zip", "ZIP"
    elif group_by == "Bedrooms" and "bedrooms" in df_norm:
        by_col, x_title = "bedrooms", "Bedrooms"

    if by_col is not None:
        agg = (df_norm.groupby(by_col, dropna=True)["price"]
               .mean().reset_index(name="avg_price")
               .sort_values("avg_price", ascending=False))
        chart = (alt.Chart(agg).mark_bar()
                 .encode(x=alt.X(f"{by_col}:N", title=x_title, sort=None),
                         y=alt.Y("avg_price:Q", title="Average Price ($)"),
                         tooltip=[alt.Tooltip(by_col, title=x_title),
                                  alt.Tooltip("avg_price", title="Average Price", format=",.0f")])
                 .properties(height=360).interactive())
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Need a ZIP or Bedrooms column to draw the chart.")

    st.subheader("Map of Homes")
    if {"latitude", "longitude"}.issubset(df_norm.columns):
        map_df = df_norm[[c for c in ["latitude", "longitude", "price",
                                      "address", "zip", "bedrooms"] if c in df_norm.columns]].copy()
        if len(map_df) > 5000:
            map_df = map_df.sample(n=5000, random_state=42)
        map_df["price_label"] = map_df["price"].map(lambda x: f"${x:,.0f}")
        if "address" not in map_df:
            map_df["address"] = "(address unavailable)"
        view_state = pdk.ViewState(
            latitude=float(map_df["latitude"].mean()),
            longitude=float(map_df["longitude"].mean()),
            zoom=10, pitch=0
        )
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_df,
            get_position="[longitude, latitude]",
            get_radius=60,
            radius_units="meters",
            pickable=True,
            auto_highlight=True,
        )
        tooltip = {
            "html": "<b>{price_label}</b><br/>{address}"
                    + ("<br/>ZIP: {zip}" if "zip" in map_df else "")
                    + ("<br/>Beds: {bedrooms}" if "bedrooms" in map_df else ""),
            "style": {"backgroundColor": "#111827", "color": "white"},
        }
        st.pydeck_chart(
            pdk.Deck(layers=[layer], initial_view_state=view_state,
                     map_style="light", tooltip=tooltip),
            use_container_width=True
        )
    else:
        st.info("Add 'latitude' and 'longitude' columns to your CSV to enable the map.")
