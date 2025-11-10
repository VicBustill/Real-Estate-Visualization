import os
import streamlit as st # type: ignore
import pandas as pd # type: ignore
import pydeck as pdk # type: ignore
from utils.io import load_first_csv

st.set_page_config(page_title="CSC 481 Real Estate Dashboard", layout="wide")
st.title("Real Estate Visualization (CSC 481)")
st.caption("Drop your real data CSVs into the `data/` folder. This app reads the first CSV it finds.")

df = load_first_csv("data")
st.write("DEBUG: DataFrame result ->", df)
st.write("DEBUG: Loaded CSVs ->", os.listdir("data"))
st.write("DEBUG: DataFrame type ->", type(df))


with st.sidebar:
    st.header("Filters")
    zip_code = st.text_input("ZIP (optional)", "")
    min_price = st.number_input("Min price", min_value=0, value=0, step=50000)
    max_price = st.number_input("Max price", min_value=0, value=2_000_000, step=50000)
    min_beds = st.number_input("Min beds", min_value=0, value=0, step=1)

if df is None:
    st.info("No data yet. Add a CSV into the `data/` folder and reload.")
else:
    q = df.copy()

    # ---- Apply filters ----
    if zip_code:
        q = q[q["zip"].astype(str).str.startswith(zip_code)]
    q = q[q["price"].between(min_price, max_price)]
    q = q[q["beds"] >= min_beds]

    st.markdown("### 📊 Filtered Data Preview")
    st.dataframe(q.head())

    # ---- Show key metrics ----
    st.markdown("### 💡 Summary Statistics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Average Price", f"${int(q['price'].mean()):,}" if not q.empty else "N/A")
    col2.metric("Lowest Price", f"${int(q['price'].min()):,}" if not q.empty else "N/A")
    col3.metric("Highest Price", f"${int(q['price'].max()):,}" if not q.empty else "N/A")

    # ---- Price distribution chart ----
    if not q.empty and "price" in q.columns and "beds" in q.columns:
        st.markdown("### 🏘️ Average Price by Bedrooms")
        avg_by_beds = q.groupby("beds")["price"].mean().reset_index()
        st.bar_chart(avg_by_beds, x="beds", y="price")

    # ---- Optional: Map ----
    if all(col in q.columns for col in ["lat", "long", "price"]):
        st.markdown("### 🗺️ Map of Listings")
        st.pydeck_chart(pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v9",
            initial_view_state=pdk.ViewState(
                latitude=q["lat"].mean(),
                longitude=q["long"].mean(),
                zoom=10,
                pitch=50,
            ),
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=q,
                    get_position='[long, lat]',
                    get_color='[200, 30, 0, 160]',
                    get_radius=200,
                ),
            ],
        ))

