# app/pages/Map3D.py
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
import pydeck as pdk
from pathlib import Path
import os

st.set_page_config(page_title="Map3D", page_icon="🗺️", layout="wide")

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

st.title("🗺️ 3D Map")
st.caption("Data source: /data (via utils.io.load_first_csv)")

st.caption(f"Map debug: total rows {len(df):,} • valid geo rows {len(m):,}")
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
