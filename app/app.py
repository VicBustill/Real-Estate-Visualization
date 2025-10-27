import os
import streamlit as st
import pandas as pd
import pydeck as pdk
from utils.io import load_first_csv

st.set_page_config(page_title="CSC 481 Real Estate Dashboard", layout="wide")
st.title("Real Estate Visualization (CSC 481)")
st.caption("Drop your real data CSVs into the `data/` folder. This app reads the first CSV it finds.")

df = load_first_csv("data")

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
    st.dataframe(q.head())
