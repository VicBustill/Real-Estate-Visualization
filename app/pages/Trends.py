# app/pages/Trends.py
from __future__ import annotations

import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Trends", page_icon="📈", layout="wide")

# ---------------- helpers ----------------


def _load_csv_from_repo() -> pd.DataFrame:
    """Use the same loader as Home so paths are consistent."""
    try:
        from utils.io import load_first_csv
    except Exception:
        import sys
        # add app/ to path
        sys.path.append(str(Path(__file__).resolve().parents[1]))
        from utils.io import load_first_csv
    try:
        return load_first_csv("data")
    except Exception as e:
        st.error(f"Could not load CSV from data/: {e}")
        return pd.DataFrame()


def fmt_money(x) -> str:
    if pd.isna(x):
        return "—"
    try:
        return f"${x:,.0f}"
    except Exception:
        return "—"


def _s(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col].astype(str).fillna("") if col in df.columns else pd.Series("", index=df.index)


# ---------------- load + light clean ----------------
df = _load_csv_from_repo()
if df.empty:
    st.warning("No data found under /data.")
    st.stop()

# essential numeric coercions
for c in ("price", "bedrooms", "bathrooms", "squareFootage", "daysOnMarket", "yearBuilt"):
    if c in df:
        df[c] = pd.to_numeric(df[c], errors="coerce")

# normalize zip as string (keep leading zeros if present)
if "zipCode" in df:
    df["zipCode"] = df["zipCode"].astype(str).str.extract(
        r"(\d{5})", expand=False).fillna(df["zipCode"].astype(str))

# $/sqft if available
if {"price", "squareFootage"}.issubset(df.columns):
    df["price_per_sqft"] = np.where(
        df["squareFootage"] > 0, df["price"] / df["squareFootage"], np.nan)

# pretty address for tables
if "formattedAddress" in df:
    df["addr"] = df["formattedAddress"].fillna("")
else:
    df["addr"] = (_s(df, "addressLine1") + ", " + _s(df, "city") +
                  ", " + _s(df, "state") + " " + _s(df, "zipCode")).str.strip(", ")

st.title("📈 Trends")

# ---------------- filters ----------------
with st.expander("Filters", expanded=True):
    c1, c2, c3, c4, c5 = st.columns(5)

    states = sorted(df.get("state", pd.Series(dtype=str)
                           ).dropna().astype(str).unique().tolist())
    state_sel = c1.multiselect("State", states, default=states or None)

    df1 = df[df["state"].astype(str).isin(
        state_sel)] if state_sel else df.copy()

    cities = sorted(df1.get("city", pd.Series(dtype=str)
                            ).dropna().astype(str).unique().tolist())
    city_sel = c2.multiselect("City", cities)

    df2 = df1[df1["city"].astype(str).isin(city_sel)] if city_sel else df1

    zips = sorted(df2.get("zipCode", pd.Series(dtype=str)
                          ).dropna().astype(str).unique().tolist())
    zip_sel = c3.multiselect("ZIP Code", zips)

    statuses = sorted(df2.get("status", pd.Series(dtype=str)
                              ).dropna().astype(str).unique().tolist())
    status_sel = c4.multiselect("Status", statuses)

    types = sorted(df2.get("propertyType", pd.Series(dtype=str)
                           ).dropna().astype(str).unique().tolist())
    type_sel = c5.multiselect("Property Type", types)

# apply filters
filtered = df2.copy()
if state_sel:
    filtered = filtered[filtered["state"].astype(str).isin(state_sel)]
if city_sel:
    filtered = filtered[filtered["city"].astype(str).isin(city_sel)]
if zip_sel:
    filtered = filtered[filtered["zipCode"].astype(str).isin(zip_sel)]
if status_sel:
    filtered = filtered[filtered["status"].astype(str).isin(status_sel)]
if type_sel:
    filtered = filtered[filtered["propertyType"].astype(str).isin(type_sel)]

if filtered.empty:
    st.warning("No listings match your filters.")
    st.stop()

# ---------------- KPIs ----------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Listings", f"{len(filtered):,}")
k2.metric("Avg Price", fmt_money(filtered["price"].mean()))
k3.metric("Median Price", fmt_money(filtered["price"].median()))
k4.metric("Avg $/sqft", fmt_money(filtered.get("price_per_sqft",
          pd.Series(dtype=float)).mean()))

st.divider()

# ---------------- NEW: show the matching listings ----------------
with st.expander(f"Listings matching your filters ({len(filtered):,})", expanded=False):
    cols = [c for c in ["addr", "city", "state", "zipCode", "price", "bedrooms", "bathrooms",
                        "squareFootage", "daysOnMarket", "status", "propertyType"] if c in filtered.columns]
    # cap rows for speed; user can download full CSV on the right
    preview = filtered[cols].copy()
    st.dataframe(preview.head(500), use_container_width=True, hide_index=True)

# ---------------- group view (ZIP vs Bedrooms) ----------------
st.markdown("View average price by…")
view = st.radio("", ("ZIP Code", "Bedrooms"),
                horizontal=True, label_visibility="collapsed")
group_col = "zipCode" if view == "ZIP Code" else "bedrooms"

if group_col not in filtered.columns or "price" not in filtered.columns:
    st.info(f"Need '{group_col}' and 'price' columns for this view.")
    st.stop()

agg = (
    filtered.dropna(subset=[group_col, "price"])
    .groupby(group_col, dropna=False)["price"]
    .agg(["count", "mean", "median"]).reset_index()
    .sort_values("mean", ascending=False)
)
st.subheader(f"Average Price by {group_col}")
st.dataframe(
    agg.rename(columns={"count": "# Listings",
               "mean": "Avg Price", "median": "Median Price"}),
    use_container_width=True, hide_index=True
)

# Pick a bar (group) to view its listings
group_options = agg[group_col].astype(str).tolist()
pick = st.selectbox(f"Show listings for {group_col}", [
                    "(select)"] + group_options, index=0)

# Chart with selection highlighted
base = agg.copy()
base["is_sel"] = np.where(base[group_col].astype(str)
                          == pick, "selected", "other")
chart = (
    alt.Chart(base)
    .mark_bar()
    .encode(
        x=alt.X(f"{group_col}:N", title=group_col, sort=None),
        y=alt.Y("mean:Q", title="Average Price ($)"),
        color=alt.Color("is_sel:N", scale=alt.Scale(
            domain=["selected", "other"], range=["#60a5fa", "#94a3b8"]), legend=None),
        tooltip=[
            alt.Tooltip(f"{group_col}", title=group_col),
            alt.Tooltip("mean", title="Average Price", format=",.0f"),
            alt.Tooltip("median", title="Median Price", format=",.0f"),
            alt.Tooltip("count", title="# Listings", format=",d"),
        ],
    )
    .properties(height=360)
    .interactive()
)
st.altair_chart(chart, use_container_width=True)

# --- NEW: listings for the selected bar/group ---
if pick != "(select)":
    sub = filtered[filtered[group_col].astype(str) == pick]
    st.markdown(
        f"**Listings for {group_col} = {pick}**  &nbsp;·&nbsp; {len(sub):,} homes")
    cols2 = [c for c in ["addr", "city", "state", "zipCode", "price", "bedrooms", "bathrooms",
                         "squareFootage", "daysOnMarket", "status", "propertyType"] if c in sub.columns]
    st.dataframe(sub[cols2].sort_values("price", ascending=False).head(
        500), use_container_width=True, hide_index=True)

# (Intentionally removed the old 'Match the Listings' section)
