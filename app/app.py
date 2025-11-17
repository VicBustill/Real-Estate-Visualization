import os
import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import pydeck as pdk  # type: ignore
from utils.io import load_first_csv


st.set_page_config(page_title="CSC 481 Real Estate Dashboard", layout="wide")
st.title("Real Estate Visualization (CSC 481)")
st.caption(
    "Drop your real data CSVs into the `data/` folder. This app reads the first CSV it finds.")

df = load_first_csv("data")
st.write("DEBUG: DataFrame result ->", df)
st.write("DEBUG: Loaded CSVs ->", os.listdir("data"))
st.write("DEBUG: DataFrame type ->", type(df))

with st.sidebar:
    st.header("Filters")
    # One of the parameters for our API 1/3
    zip_code = st.text_input("ZIP (optional)", "")
    # One of the parameters for our API 2/3
    state = st.text_input("Abbreviated State", "")
    city = st.text_input("City", "")  # One of the parameters for our API 3/3
    min_price = st.number_input("Min price", min_value=0, value=0, step=50000)
    max_price = st.number_input(
        "Max price", min_value=0, value=2_000_000, step=50000)
    min_beds = st.number_input("Min beds", min_value=0, value=0, step=1)
    max_beds = st.number_input("Min beds", min_value=0, value=0, step=1)

# ______________This section will make the API call ________________________


# _________________________________________________________________________
# if df is None:
    # st.info("No data yet. Add a CSV into the `data/` folder and reload.")
# else:
    # q = df.copy()
    # st.dataframe(q.head())

    # fixing the CSV data
if df is None:
    st.info("No data yet. Add a CSV into the `data/` folder and reload.")
else:
    q = df.copy()
    # st.dataframe(q.head())
    # uppercase or lowercase should not matter
    q.columns = q.columns = [str(c).strip().lower() for c in q.columns]

    # this will help find important columns for zip, price, and beds
    zip_columns = None
    for name in ["zip", "zipcode", "postal_code"]:
        if name in q.columns:
            zip_columns = name
            break

    price_columns = None
    for name in ["price", "list_price", "listprice"]:
        if name in q.columns:
            price_columns = name
            break

    bed_columns = None
    for name in ["beds", "bedrooms", "br"]:
        if name in q.columns:
            bed_columns = name
            break

    # whatever the user chooses in the sidebar should appear
    if zip_code and zip_columns:
        # use the ZIP column name we detected, and filter rows whose ZIP starts with the user input
        q = q[q[zip_columns].astype(str).str.startswith(zip_code)]

    if price_columns:
        q = q[(q[price_columns] >= min_price) &
              (q[price_columns] <= max_price)]

    if bed_columns:
        q = q[q[bed_columns] >= min_beds]

    st.subheader("Match the Listings")
    st.dataframe(q)

    # not sure if yall are up for it but maybe we can implement a chart displaying these listings or whatnot
